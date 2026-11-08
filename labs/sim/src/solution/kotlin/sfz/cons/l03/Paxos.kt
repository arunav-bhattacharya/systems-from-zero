package sfz.cons.l03

/**
 * Lesson cons-03: single-decree Paxos, as in Lamport's "Paxos Made Simple". Several proposers each
 * want a different value chosen (here: what to do with payment pay-77, "capture" or "void"), a set
 * of acceptors votes, and every proposer that learns a decision must learn the same one.
 */

/** A proposal number. Higher round wins; the proposer id breaks ties, so no two proposers share one. */
data class Ballot(val round: Int, val proposer: Int) : Comparable<Ballot> {
    override fun compareTo(other: Ballot) = compareValuesBy(this, other, { it.round }, { it.proposer })
    override fun toString() = "$round.$proposer"
}

sealed interface Message

/** Phase 1a: "promise not to accept anything numbered below [ballot]". */
data class Prepare(val ballot: Ballot) : Message

/** Phase 1b: "promised; the last proposal I accepted was [accepted] with [value]" (both null if none). */
data class Promise(val ballot: Ballot, val accepted: Ballot?, val value: String?) : Message

/** Phase 2a: "accept [value] under [ballot]". */
data class Accept(val ballot: Ballot, val value: String) : Message

/** Phase 2b: "accepted [ballot]". */
data class Accepted(val ballot: Ballot, val value: String) : Message

/** "No: I have promised [promised], which is higher than your [ballot]." */
data class Reject(val ballot: Ballot, val promised: Ballot) : Message

/**
 * An acceptor. Its three fields are its durable state: the harness treats them as written to disk
 * before any reply leaves, so they survive a crash.
 */
class Acceptor(val id: Int) {
    var promised: Ballot? = null
    var acceptedBallot: Ballot? = null
    var acceptedValue: String? = null

    /**
     * Exercise 1a. If [m]'s ballot is at least as high as anything promised so far (or nothing has
     * been promised), promise it and answer with a [Promise] carrying the last accepted proposal.
     * Otherwise answer [Reject] with what you did promise.
     */
    fun onPrepare(m: Prepare): Message {
        val p = promised
        if (p != null && m.ballot < p) return Reject(m.ballot, p)       // promised someone higher
        promised = m.ballot                                              // durable before the reply leaves
        return Promise(m.ballot, acceptedBallot, acceptedValue)          // and tell what I accepted last
    }

    /**
     * Exercise 1b. Accept [m] unless you have promised a higher ballot: remember the ballot and value,
     * and raise [promised] to it. Answer [Accepted], or [Reject].
     */
    fun onAccept(m: Accept): Message {
        val p = promised
        if (p != null && m.ballot < p) return Reject(m.ballot, p)
        promised = m.ballot
        acceptedBallot = m.ballot
        acceptedValue = m.value
        return Accepted(m.ballot, m.value)
    }
}

/**
 * A proposer for one round at a time. The harness ([runPaxos]) calls [startRound], sends the
 * [Prepare] to every acceptor, and feeds the answers back in.
 */
class Proposer(val id: Int, val value: String, private val acceptors: Int) {
    val majority = acceptors / 2 + 1
    var ballot = Ballot(0, id)
        private set
    var decided: String? = null
        private set
    private var highestRoundSeen = 0

    /** Promises for the current [ballot], by acceptor id (an acceptor's duplicate counts once). */
    val promises = mutableMapOf<Int, Promise>()

    /** Acceptors that accepted the current [ballot]. */
    val accepts = mutableSetOf<Int>()

    /** The value this round asked acceptors to accept, once phase 2 has started. */
    var proposed: String? = null

    /** Starts a new round with a ballot higher than any this proposer has seen (given). */
    fun startRound(): Prepare {
        ballot = Ballot(maxOf(ballot.round, highestRoundSeen) + 1, id)
        promises.clear()
        accepts.clear()
        proposed = null
        return Prepare(ballot)
    }

    /** Remembers how high other proposers have gone; true if this round has been overtaken (given). */
    fun onReject(m: Reject): Boolean {
        highestRoundSeen = maxOf(highestRoundSeen, m.promised.round)
        return m.ballot == ballot && decided == null
    }

    /**
     * Exercise 2. Ignore promises for any ballot but the current one. Count each acceptor once. When
     * the promises first reach a [majority], pick the value with [chooseValue], store it in
     * [proposed] and return the [Accept] to send to every acceptor. Return null otherwise (also for
     * any promise after phase 2 has started).
     */
    fun onPromise(from: Int, m: Promise, choose: (String, Collection<Promise>) -> String = ::chooseValue): Accept? {
        if (m.ballot != ballot || proposed != null) return null          // an old round, or phase 2 already started
        promises[from] = m                                               // a duplicate overwrites, so it counts once
        if (promises.size < majority) return null
        val v = choose(value, promises.values)                           // the safety rule
        proposed = v
        return Accept(ballot, v)
    }

    /**
     * Exercise 3. Count [Accepted] answers for the current ballot, each acceptor once. When they reach
     * a [majority], the value is chosen: set [decided] to [proposed] and return it. Otherwise null.
     */
    fun onAccepted(from: Int, m: Accepted): String? {
        if (m.ballot != ballot || decided != null) return null
        accepts += from
        if (accepts.size < majority) return null
        decided = proposed                                               // a majority accepted one ballot: chosen
        return decided
    }
}

/**
 * Exercise 2, the rule that makes Paxos safe. Among [promises], find the one with the highest
 * accepted ballot and return its value. If no acceptor has accepted anything, the proposer may use
 * its [own] value.
 */
fun chooseValue(own: String, promises: Collection<Promise>): String =
    promises.filter { it.accepted != null }.maxByOrNull { it.accepted!! }?.value ?: own

/** Knobs for one run of [runPaxos] (given). */
data class PaxosConfig(
    val seed: Long,
    val acceptors: Int = 5,
    val values: List<String> = listOf("capture", "void"),
    val dropRate: Double = 0.0,
    val duplicateRate: Double = 0.0,
    val minDelayMs: Long = 1,
    val maxDelayMs: Long = 10,
    /** At most this many acceptors are down at once; each crash lasts 20 to 200 ms. */
    val maxDown: Int = 0,
    /** Every proposer except the last may crash at a random moment in its first 100 ms. */
    val proposersCrash: Boolean = false,
    /** A round that hasn't decided after this long is abandoned. */
    val timeoutMs: Long = 60,
    /** Wait a random 0 to timeoutMs before retrying (true) or retry at once (false). */
    val randomBackoff: Boolean = true,
    /** Acceptors that forget their state when they restart: what happens without fsync. */
    val acceptorsForget: Boolean = false,
    val giveUpAtMs: Long = 20_000,
)

/** What happened in one run (given). */
class PaxosOutcome(
    /** proposer id -> the value it learned was chosen */
    val decisions: Map<Int, String>,
    /** every value that a majority of acceptors accepted under one ballot, whether or not anyone learned it */
    val chosen: Set<String>,
    val rounds: Int,
    val messages: Long,
    val firstDecisionAtMs: Long?,
    /** milliseconds from sending Accept to learning the decision, for the deciding rounds */
    val phase2Ms: List<Long>,
    /** milliseconds from sending Prepare to learning the decision, for the deciding rounds */
    val roundMs: List<Long>,
)

/**
 * Runs single-decree Paxos on a simulated network (given). Proposer i proposes `values[i]`, starting
 * at a random moment in the first 20 ms. Each round: Prepare to all, then (via your code) Accept to
 * all, and a timer; on a timeout or a Reject that overtakes the round, the proposer starts a new one.
 */
fun runPaxos(c: PaxosConfig, choose: (String, Collection<Promise>) -> String = ::chooseValue): PaxosOutcome {
    val sim = Sim(c.seed)
    val net = Network(sim, c.minDelayMs, c.maxDelayMs, c.dropRate, c.duplicateRate)
    val acceptors = MutableList(c.acceptors) { Acceptor(it) }
    val up = BooleanArray(c.acceptors) { true }
    val proposers = c.values.mapIndexed { i, v -> Proposer(i, v, c.acceptors) }
    val alive = BooleanArray(proposers.size) { true }
    val acceptedBy = mutableMapOf<Ballot, MutableSet<Int>>()   // who accepted each ballot: a majority means chosen
    val ballotValue = mutableMapOf<Ballot, String>()
    var rounds = 0
    var firstDecision: Long? = null
    val prepareSentAt = mutableMapOf<Int, Long>()
    val acceptSentAt = mutableMapOf<Int, Long>()
    val phase2 = mutableListOf<Long>()
    val whole = mutableListOf<Long>()

    fun done() = proposers.indices.all { !alive[it] || proposers[it].decided != null }

    lateinit var startRound: (Int) -> Unit

    /** An acceptor's answer travels back to proposer [p], who may then send the next phase. */
    fun reply(p: Int, from: Int, m: Message): Unit = net.send {
        val prop = proposers[p]
        if (!alive[p] || prop.decided != null) return@send
        when (m) {
            is Promise -> prop.onPromise(from, m, choose)?.let { accept ->
                acceptSentAt[p] = sim.now
                for (a in acceptors.indices) net.send {
                    if (!up[a]) return@send                              // a crashed acceptor hears nothing
                    val answer = acceptors[a].onAccept(accept)
                    if (answer is Accepted) {
                        acceptedBy.getOrPut(answer.ballot) { mutableSetOf() } += a
                        ballotValue[answer.ballot] = answer.value
                    }
                    reply(p, a, answer)
                }
            }
            is Accepted -> prop.onAccepted(from, m)?.let {
                if (firstDecision == null) firstDecision = sim.now
                acceptSentAt[p]?.let { t -> phase2 += sim.now - t }
                prepareSentAt[p]?.let { t -> whole += sim.now - t }
            }
            is Reject -> if (prop.onReject(m)) startRound(p)
            else -> error("a proposer doesn't expect $m")
        }
    }

    startRound = { p ->
        val delay = if (c.randomBackoff) sim.random.nextLong(0, c.timeoutMs + 1) else 0L
        sim.after(delay) {
            val prop = proposers[p]
            if (alive[p] && prop.decided == null) {
                rounds++
                val prepare = prop.startRound()
                prepareSentAt[p] = sim.now
                for (a in acceptors.indices) net.send {
                    if (up[a]) reply(p, a, acceptors[a].onPrepare(prepare))
                }
                val mine = prop.ballot
                sim.after(c.timeoutMs) { if (prop.ballot == mine && prop.decided == null) startRound(p) }
            }
        }
    }

    for (p in proposers.indices) sim.after(sim.random.nextLong(0, 21)) { startRound(p) }
    if (c.proposersCrash) for (p in 0 until proposers.size - 1) {
        sim.after(sim.random.nextLong(0, 101)) { alive[p] = false }
    }
    fun crashSomeone() {
        sim.after(sim.random.nextLong(5, 60)) {
            val upNow = acceptors.indices.filter { up[it] }
            if (acceptors.size - upNow.size < c.maxDown) {
                val a = upNow.random(sim.random)
                up[a] = false
                sim.after(sim.random.nextLong(20, 201)) {
                    if (c.acceptorsForget) acceptors[a] = Acceptor(a)   // restarted without its disk
                    up[a] = true
                }
            }
            if (!done()) crashSomeone()
        }
    }
    if (c.maxDown > 0) crashSomeone()
    sim.run(c.giveUpAtMs) { done() }

    val majority = c.acceptors / 2 + 1
    return PaxosOutcome(
        decisions = proposers.filter { it.decided != null }.associate { it.id to it.decided!! },
        chosen = acceptedBy.filter { it.value.size >= majority }.keys.map { ballotValue.getValue(it) }.toSet(),
        rounds = rounds,
        messages = net.sent,
        firstDecisionAtMs = firstDecision,
        phase2Ms = phase2,
        roundMs = whole,
    )
}
