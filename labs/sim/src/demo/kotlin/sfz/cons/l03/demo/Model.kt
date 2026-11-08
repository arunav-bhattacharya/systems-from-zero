// Copies of the lab's given code, the reference answers and the test checker, so the demos run
// without your solution. Demos don't see src/main, src/solution or src/test.
package sfz.cons.l03.demo

import java.util.PriorityQueue
import kotlin.random.Random


/**
 * Virtual time for lesson cons-03 (given). Nothing sleeps: [run] takes the scheduled events in time
 * order and moves [now] from one to the next. All randomness comes from [random], seeded, so one
 * seed replays exactly the same run. Two events at the same millisecond run in the order added.
 */
class Sim(seed: Long) {
    val random = Random(seed)
    var now: Long = 0
        private set

    private class Event(val at: Long, val seq: Long, val action: () -> Unit)

    private var seq = 0L
    private val queue = PriorityQueue(compareBy<Event>({ it.at }, { it.seq }))

    fun after(delayMs: Long, action: () -> Unit) {
        queue += Event(now + delayMs, seq++, action)
    }

    /** Runs events until none are left, [stop] says so, or the clock passes [untilMs]. */
    fun run(untilMs: Long = Long.MAX_VALUE, stop: () -> Boolean = { false }) {
        while (queue.isNotEmpty() && queue.peek().at <= untilMs && !stop()) {
            val e = queue.poll()
            now = e.at
            e.action()
        }
    }
}

/**
 * An unreliable network (given). Each message is lost with probability [dropRate], delivered twice
 * with probability [duplicateRate], and otherwise arrives after [minMs] to [maxMs]. Messages overtake
 * each other freely. [sent] counts messages handed to the network.
 */
class Network(
    private val sim: Sim,
    private val minMs: Long = 1,
    private val maxMs: Long = 10,
    private val dropRate: Double = 0.0,
    private val duplicateRate: Double = 0.0,
) {
    var sent = 0L
        private set

    fun send(deliver: () -> Unit) {
        sent++
        val r = sim.random
        if (r.nextDouble() < dropRate) return
        sim.after(r.nextLong(minMs, maxMs + 1), deliver)
        if (r.nextDouble() < duplicateRate) sim.after(r.nextLong(minMs, maxMs + 1), deliver)
    }
}


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


/**
 * Lesson cons-03, part 2: a linearizable compare-and-set register built on total order broadcast.
 *
 * Every replica receives the same commands in the same order and applies them with the same
 * deterministic code, so every replica computes the same result for every command. A client sends
 * its command into the log and waits until its own replica applies it: the result is the answer.
 */
sealed interface Command {
    val id: Long
    val client: String
}

/** "If the register holds [expected], set it to [value]." */
data class Cas(override val id: Long, override val client: String, val expected: String?, val value: String) : Command

/** A read that goes through the log like any other command. */
data class Read(override val id: Long, override val client: String) : Command

/**
 * Total order broadcast with a fixed sequencer (given). [broadcast] sends a command to the
 * sequencer, which numbers it 1, 2, 3... and sends it to every replica. Messages overtake each other
 * on the way, so each replica holds back a command until it has delivered every lower number.
 *
 * This is the simplest version that works, and its sequencer is a single point of failure: if it
 * dies, nothing is ever delivered again. Making the sequencer fault tolerant is consensus, one
 * Paxos instance per log slot (Multi-Paxos), or Raft.
 */
class TotalOrderBroadcast(
    private val net: Network,
    replicas: Int,
    private val deliver: (replica: Int, Command) -> Unit,
) {
    private var next = 1L
    private val delivered = LongArray(replicas)
    private val waiting = List(replicas) { sortedMapOf<Long, Command>() }

    fun broadcast(cmd: Command) = net.send {
        val seq = next++                                    // the sequencer decides the order
        for (r in waiting.indices) net.send { arrive(r, seq, cmd) }
    }

    private fun arrive(r: Int, seq: Long, cmd: Command) {
        waiting[r][seq] = cmd
        while (waiting[r].isNotEmpty() && waiting[r].firstKey() == delivered[r] + 1) {
            val c = waiting[r].remove(waiting[r].firstKey())!!
            delivered[r]++
            deliver(r, c)
        }
    }
}

/** One replica's copy of the register, and the state machine that changes it. */
class Replica(val name: String) {
    var value: String? = null
        private set
    val applied = mutableListOf<Command>()

    /**
     * Exercise 4. Apply [cmd] and return the value the register held just BEFORE it (this is what
     * Java's `compareAndExchange` returns). A [Cas] sets [value] only if that previous value equals
     * its `expected`; a [Read] changes nothing. Record every command in [applied].
     */
    fun apply(cmd: Command): String? {
        val before = value
        if (cmd is Cas && before == cmd.expected) value = cmd.value   // same input, same order: same result everywhere
        applied += cmd
        return before
    }
}

/**
 * Three replicas behind a total order broadcast. Each client is attached to one replica (its home):
 * c1 to r1, c2 to r2 and so on, round robin.
 */
class LogRegister(private val net: Network) {
    val replicas = listOf(Replica("r1"), Replica("r2"), Replica("r3"))
    private val pending = mutableMapOf<Long, (String?) -> Unit>()
    private var nextId = 1L
    private val tob = TotalOrderBroadcast(net, replicas.size) { r, cmd -> onDeliver(r, cmd) }

    fun home(client: String): Int = (client.removePrefix("c").toInt() - 1) % replicas.size

    /** Every replica applies every command; the client's home replica also sends the result back (given). */
    private fun onDeliver(r: Int, cmd: Command) {
        val before = replicas[r].apply(cmd)
        if (r == home(cmd.client)) pending.remove(cmd.id)?.let { done -> net.send { done(before) } }
    }

    /**
     * Exercise 5. Put [cmd] in the log and arrange for [done] to be called with the result once the
     * client's home replica applies it ([onDeliver] does the calling: it looks in [pending]).
     */
    fun submit(cmd: Command, done: (String?) -> Unit) {
        pending[cmd.id] = done        // answered when the home replica applies it, not before
        tob.broadcast(cmd)
    }

    /** Compare-and-set through the log, answering with the value before it (given). */
    fun compareAndExchange(client: String, expected: String?, value: String, done: (String?) -> Unit) =
        submit(Cas(nextId++, client, expected, value), done)

    /** Compare-and-set through the log, answering whether it swapped (given). */
    fun cas(client: String, expected: String?, value: String, done: (Boolean) -> Unit) =
        compareAndExchange(client, expected, value) { before -> done(before == expected) }

    /** A read through the log (given): linearizable, and as slow as a write. */
    fun read(client: String, done: (String?) -> Unit) = submit(Read(nextId++, client), done)

    /** A read of the home replica's current copy, skipping the log (given): fast, and not linearizable. */
    fun localRead(client: String, done: (String?) -> Unit) = net.send {
        val v = replicas[home(client)].value
        net.send { done(v) }
    }
}

/**
 * Exercise 6: consensus from compare-and-set. Every proposer tries `null -> value` on a fresh
 * register with [LogRegister.compareAndExchange]. Exactly one succeeds. Call [done] with the decided
 * value: yours if the register was empty before your CAS, otherwise what was there (the winner's).
 */
fun propose(register: LogRegister, client: String, value: String, done: (String) -> Unit) =
    register.compareAndExchange(client, null, value) { before -> done(before ?: value) }   // first CAS in the log wins


/** One operation on the register, as a client saw it (test helper). */
data class Op(
    val start: Long,
    val end: Long,
    val cas: Boolean,
    val value: String?,
    val expected: String? = null,
    val ok: Boolean = true,
)

/**
 * A small Wing and Gong style checker for a register with read and compare-and-set (test helper, the
 * same search as lesson cons-02's lab): place a minimal operation whose answer fits the state, go
 * deeper, take it back on a dead end, and never explore the same (placed set, value) twice.
 */
fun linearizable(ops: List<Op>): Boolean {
    val all = ops.sortedBy { it.start }
    val placed = BooleanArray(all.size)
    val seen = HashSet<Pair<List<Boolean>, String?>>()
    fun go(count: Int, state: String?): Boolean {
        if (count == all.size) return true
        if (!seen.add(placed.toList() to state)) return false
        val minEnd = all.indices.filter { !placed[it] }.minOf { all[it].end }
        for (i in all.indices) {
            if (placed[i] || all[i].start > minEnd) continue
            val op = all[i]
            val next = when {
                !op.cas -> if (op.value == state) state else continue
                state == op.expected -> if (op.ok) op.value else continue
                else -> if (!op.ok) state else continue
            }
            placed[i] = true
            if (go(count + 1, next)) return true
            placed[i] = false
        }
        return false
    }
    return go(0, null)
}
