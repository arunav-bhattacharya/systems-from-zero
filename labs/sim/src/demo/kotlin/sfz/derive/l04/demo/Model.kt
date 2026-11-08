package sfz.derive.l04.demo

// The demos carry their own copy of the lab's model, with the exercises finished.
// Do the lab first if you want to write ClaimProcessor and WalletProcessor yourself.

import kotlin.random.Random

/**
 * A seeded, deterministic scheduler (finished; nothing to write here).
 *
 * Each task is a block of code that calls `yield(Unit)` wherever another task may run in between:
 * a network round trip, a poll of a log. At every tick the scheduler picks one live task with its
 * seeded [Random] and runs it up to its next `yield`. The same seed gives the same interleaving,
 * so every count in the tests is exact and the same on every laptop.
 */
class Scheduler(seed: Long) {
    private val rnd = Random(seed)
    private val live = ArrayList<Iterator<Unit>>()

    /** Steps run so far: the simulation's clock. */
    var now = 0L
        private set

    /** Adds a task. It starts running at the next tick that picks it. */
    fun spawn(body: suspend SequenceScope<Unit>.() -> Unit) {
        live += iterator(body)
    }

    /** Runs until every task has finished. [maxSteps] guards against a simulation that never ends. */
    fun run(maxSteps: Long = 50_000_000) {
        while (live.isNotEmpty()) {
            check(now < maxSteps) { "the simulation did not finish in $maxSteps steps" }
            val i = rnd.nextInt(live.size)
            val task = live[i]
            if (task.hasNext()) {           // runs the task up to its next yield
                task.next()
            } else {                        // the task has finished: swap-remove it
                live[i] = live[live.size - 1]
                live.removeAt(live.size - 1)
            }
            now++
        }
    }
}

/** The value below which [p] of the [values] fall (nearest rank). */
fun percentile(values: List<Long>, p: Double): Long {
    if (values.isEmpty()) return 0
    val sorted = values.sorted()
    val rank = Math.ceil(p * sorted.size).toInt().coerceIn(1, sorted.size)
    return sorted[rank - 1]
}

/** A user asks for a handle, such as `@ana`. [requestId] is made by the client and kept across retries. */
data class Claim(val requestId: String, val userId: String, val username: String)

/** The answer a client waits for. */
sealed interface Decision {
    val requestId: String
    val username: String
}

data class Granted(override val requestId: String, override val username: String, val userId: String) : Decision

data class Rejected(override val requestId: String, override val username: String, val takenBy: String) : Decision

/** What a run produced: every decision a client received, and how long each client waited (in scheduler steps). */
class ClaimRun(val decisions: List<Decision>, val waits: List<Long>) {
    /** Handles granted to more than one user, counted as extra owners: two owners of `@ana` is 1. */
    val duplicates: Int
        get() = decisions.filterIsInstance<Granted>()
            .groupBy { it.username }
            .values.sumOf { grants -> grants.map { it.userId }.distinct().size - 1 }

    val granted: Int get() = decisions.count { it is Granted }
}

/** [users] users, each claiming one handle drawn from [names] popular ones, so many users want the same handle. */
object Workload {
    fun claims(seed: Long, users: Int = 2_000, names: Int = 200): List<Claim> {
        val rnd = Random(seed)
        return (0 until users).map { u -> Claim("req-$u", "u-$u", "name-${rnd.nextInt(names)}") }
    }
}

/**
 * The race (finished). [servers] app servers share one table that has no unique constraint. Each
 * server checks whether the handle is free, then inserts it. Between the SELECT and the INSERT
 * there is a round trip to the database (the `yield`), and in that gap another server can run
 * its own check and see the handle as free too.
 */
fun checkThenInsert(claims: List<Claim>, servers: Int, seed: Long): ClaimRun {
    val table = LinkedHashMap<String, MutableList<String>>()    // handle -> the users holding it
    val decisions = ArrayList<Decision>()
    val waits = ArrayList<Long>()
    val sched = Scheduler(seed)
    for (s in 0 until servers) {
        val mine = claims.filterIndexed { i, _ -> i % servers == s }
        sched.spawn {
            for (c in mine) {
                val start = sched.now
                val holder = table[c.username]?.firstOrNull()   // SELECT user_id FROM handles WHERE name = ?
                yield(Unit)                                     // the round trip: anyone may run here
                if (holder == null) {
                    table.getOrPut(c.username) { mutableListOf() } += c.userId   // INSERT INTO handles ...
                    decisions += Granted(c.requestId, c.username, c.userId)
                } else {
                    decisions += Rejected(c.requestId, c.username, holder)
                }
                waits += sched.now - start
                yield(Unit)
            }
        }
    }
    sched.run()
    return ClaimRun(decisions, waits)
}

/**
 * Exercise 1. Which of [partitions] partitions a key goes to: the key's `hashCode()` modulo the
 * partition count, always in `0 until partitions`.
 *
 * Use `Math.floorMod`, not `abs(hashCode) % partitions`: `abs(Int.MIN_VALUE)` is still negative.
 */
fun partitionFor(key: String, partitions: Int): Int =
    Math.floorMod(key.hashCode(), partitions)                    // same key, same partition, every time

/**
 * Exercise 2. One partition's processor. It is single-threaded and reads its partition in order,
 * so for every handle routed to it, it alone decides, one claim at a time. That is the whole trick.
 *
 * Its state is derived only from the claims it has read, so a fresh processor that replays the
 * partition from offset 0 rebuilds the same state and makes the same decisions.
 */
class ClaimProcessor {
    private val owner = HashMap<String, String>()               // handle -> userId that holds it
    private val decided = HashMap<String, Decision>()           // requestId -> the answer already given

    /**
     * Decides one claim:
     * - a requestId it has seen before gets exactly the answer it got the first time (a redelivery
     *   or a client retry must not change anything);
     * - a free handle, or one this same user already holds, is [Granted] to the claimant;
     * - otherwise it is [Rejected], naming the user who holds it.
     */
    fun decide(claim: Claim): Decision {
        decided[claim.requestId]?.let { return it }             // seen it: same answer, no new effect
        val holder = owner[claim.username]
        val decision = if (holder == null || holder == claim.userId) {
            owner[claim.username] = claim.userId                // the first claim in log order wins
            Granted(claim.requestId, claim.username, claim.userId)
        } else {
            Rejected(claim.requestId, claim.username, holder)
        }
        decided[claim.requestId] = decision
        return decision
    }
}

/**
 * Claims through a partitioned log (finished). Each of [clients] clients appends its claim to the
 * partition that [keyOf] picks, then waits for its decision. One [ClaimProcessor] per partition
 * reads that partition in order and answers. Route by the handle, and every claim for one handle
 * meets the same processor. Route by anything else, and two processors can each grant it.
 */
fun throughLog(
    claims: List<Claim>,
    clients: Int,
    partitions: Int,
    seed: Long,
    keyOf: (Claim) -> String = Claim::username,
): ClaimRun {
    val logs = List(partitions) { ArrayList<Claim>() }
    val replies = HashMap<String, Decision>()
    val decisions = ArrayList<Decision>()
    val waits = ArrayList<Long>()
    var clientsDone = 0
    val sched = Scheduler(seed)
    for (c in 0 until clients) {
        val mine = claims.filterIndexed { i, _ -> i % clients == c }
        sched.spawn {
            for (claim in mine) {
                val start = sched.now
                logs[partitionFor(keyOf(claim), partitions)] += claim   // one append: the request is now durable
                yield(Unit)
                while (claim.requestId !in replies) yield(Unit)          // the timeliness cost: wait for the answer
                decisions += replies.getValue(claim.requestId)
                waits += sched.now - start
            }
            clientsDone++
        }
    }
    for (p in 0 until partitions) {
        sched.spawn {
            val processor = ClaimProcessor()
            var offset = 0
            while (clientsDone < clients || offset < logs[p].size) {
                if (offset < logs[p].size) {
                    val d = processor.decide(logs[p][offset++])
                    replies[d.requestId] = d
                }
                yield(Unit)
            }
        }
    }
    sched.run()
    return ClaimRun(decisions, waits)
}

/** Move [amount] cents from wallet [from] to wallet [to]. [requestId] is made by the client. */
data class Transfer(val requestId: String, val from: String, val to: String, val amount: Long)

/** What travels through a wallet partition's log. */
sealed interface Message {
    val requestId: String
}

/** A client's request. It is appended once, to the partition of the wallet the money leaves. */
data class Requested(val transfer: Transfer) : Message {
    override val requestId: String get() = transfer.requestId
}

/** Written by the source wallet's processor into the destination wallet's partition. */
data class Credit(override val requestId: String, val wallet: String, val amount: Long) : Message

/** The answer a client waits for. */
sealed interface Outcome {
    val requestId: String
}

data class Accepted(override val requestId: String) : Outcome

data class Declined(override val requestId: String, val reason: String) : Outcome

/** A copy of a processor's state, taken every few messages so a crash loses only the work since. */
class Checkpoint(
    val balances: Map<String, Long>,
    val outcomes: Map<String, Outcome>,
    val creditsApplied: Set<String>,
)

/**
 * Exercise 3. The processor of one wallet partition. It owns the balances of the wallets routed
 * to it and is the only thing that changes them. It reads its partition in order, one message at
 * a time, and its state comes only from those messages, so after a crash it can restore a
 * [Checkpoint], read the same messages again, and make the same decisions.
 */
class WalletProcessor(initial: Map<String, Long>, private val dedupe: Boolean = true) {
    val balances = LinkedHashMap(initial)
    private val outcomes = HashMap<String, Outcome>()       // requestId -> the decision already made
    private val creditsApplied = HashSet<String>()          // requestIds whose credit is already in balances

    /** True once the credit of [requestId] is in this partition's balances. */
    fun hasCredit(requestId: String) = requestId in creditsApplied

    /**
     * Handles one message from this partition's log.
     *
     * A [Requested] transfer:
     * - if this requestId was already decided (the client appended it twice), [reply] with the
     *   same outcome again and change nothing;
     * - if the source wallet holds at least the amount, take the money out, [send] a [Credit] for
     *   the destination with the same requestId, and reply [Accepted];
     * - otherwise reply [Declined] with the reason "insufficient funds".
     *
     * A [Credit]: add it to the wallet, unless this requestId's credit is already applied (a
     * replayed source processor sent it twice). Credits need no reply.
     */
    fun handle(msg: Message, send: (Credit) -> Unit, reply: (Outcome) -> Unit) {
        when (msg) {
            is Requested -> {
                if (dedupe) outcomes[msg.requestId]?.let { reply(it); return }   // a duplicate request: same answer
                val t = msg.transfer
                val balance = balances.getValue(t.from)
                val outcome = if (balance >= t.amount) {
                    balances[t.from] = balance - t.amount                    // the debit is local to this partition
                    send(Credit(t.requestId, t.to, t.amount))                // the credit travels, with the same id
                    Accepted(t.requestId)
                } else {
                    Declined(t.requestId, "insufficient funds")
                }
                outcomes[t.requestId] = outcome
                reply(outcome)
            }
            is Credit -> {
                if (!creditsApplied.add(msg.requestId) && dedupe) return    // seen this credit: drop the duplicate
                balances[msg.wallet] = balances.getValue(msg.wallet) + msg.amount
            }
        }
    }

    fun checkpoint() = Checkpoint(LinkedHashMap(balances), HashMap(outcomes), HashSet(creditsApplied))

    fun restore(cp: Checkpoint) {
        balances.clear(); balances.putAll(cp.balances)
        outcomes.clear(); outcomes.putAll(cp.outcomes)
        creditsApplied.clear(); creditsApplied.addAll(cp.creditsApplied)
    }
}

/** The knobs of one run. */
data class TransferConfig(
    val wallets: Int = 40,
    val partitions: Int = 4,
    val transfers: Int = 1_000,
    val clients: Int = 16,
    val initialBalance: Long = 10_000,
    /** After each message, the chance that its processor crashes and restarts from its last checkpoint. */
    val crashChance: Double = 0.01,
    val checkpointEvery: Int = 25,
    /** The chance that a client times out and sends its transfer a second time. */
    val clientRetryChance: Double = 0.05,
    /** Separate-steps design only: the chance that the API crashes between writing the debit and the credit. */
    val apiCrashChance: Double = 0.02,
    val seed: Long = 7,
    /** Demo only: false makes the processors apply duplicates, as `balance += amount` without request ids would. */
    val dedupe: Boolean = true,
) {
    val expectedTotal: Long get() = wallets * initialBalance
}

fun wallet(i: Int) = "w-%02d".format(i)

/** The same seeded transfers for both designs: amounts from 1.00 to 60.00 between 40 wallets. */
fun transfersFor(config: TransferConfig): List<Transfer> {
    val rnd = Random(config.seed)
    val wallets = (0 until config.wallets).map(::wallet)
    return (0 until config.transfers).map { i ->
        val from = wallets[rnd.nextInt(wallets.size)]
        var to = wallets[rnd.nextInt(wallets.size)]
        while (to == from) to = wallets[rnd.nextInt(wallets.size)]
        Transfer("t-$i", from, to, 100L * (1 + rnd.nextInt(60)))
    }
}

/** What a run of the logged-request design produced. */
class TransferRun(
    val config: TransferConfig,
    val transfers: List<Transfer>,
    val balances: Map<String, Long>,
    val outcomes: Map<String, Outcome>,
    /** Credit messages written into logs, duplicates included. */
    val creditsSent: Int,
    val crashes: Int,
    /** Replies that disagreed with an earlier reply for the same requestId. Must be 0. */
    val conflictingReplies: Int,
) {
    val totalMoney: Long get() = balances.values.sum()
    val accepted: Int get() = outcomes.values.count { it is Accepted }
}

/**
 * Runs wallet-to-wallet transfers through a partitioned log (finished). Clients append each
 * [Requested] to the source wallet's partition and wait for the outcome; one [WalletProcessor] per
 * partition reads its log in order, checkpoints its state together with its offset every
 * [TransferConfig.checkpointEvery] messages, and sometimes crashes after a message, losing the
 * work since its last checkpoint. Replays after a crash send some credits a second time.
 */
fun runTransfers(config: TransferConfig): TransferRun {
    val crashRnd = Random(config.seed + 1)
    val wallets = (0 until config.wallets).map(::wallet)
    val transfers = transfersFor(config)
    fun part(w: String) = partitionFor(w, config.partitions)

    val logs = List(config.partitions) { ArrayList<Message>() }
    val processors = List(config.partitions) { p ->
        WalletProcessor(wallets.filter { part(it) == p }.associateWith { config.initialBalance }, config.dedupe)
    }
    val positions = IntArray(config.partitions)
    val outcomes = LinkedHashMap<String, Outcome>()
    var creditsSent = 0
    var crashes = 0
    var conflictingReplies = 0
    var clientsDone = 0
    val sched = Scheduler(config.seed)

    for (c in 0 until config.clients) {
        val mine = transfers.filterIndexed { i, _ -> i % config.clients == c }
        val retry = Random(config.seed * 31 + c)
        sched.spawn {
            for (t in mine) {
                logs[part(t.from)] += Requested(t)                          // the one write the client makes
                yield(Unit)
                if (retry.nextDouble() < config.clientRetryChance) {       // timed out: append it again
                    logs[part(t.from)] += Requested(t)
                    yield(Unit)
                }
                while (t.requestId !in outcomes) yield(Unit)
            }
            clientsDone++
        }
    }
    for (p in 0 until config.partitions) {
        sched.spawn {
            val proc = processors[p]
            var cp = proc.checkpoint()
            var cpOffset = 0
            var sinceCp = 0
            fun allCaughtUp() = (0 until config.partitions).all { positions[it] == logs[it].size }
            while (clientsDone < config.clients || !allCaughtUp()) {
                if (positions[p] < logs[p].size) {
                    val msg = logs[p][positions[p]]
                    proc.handle(
                        msg,
                        send = { credit -> logs[part(credit.wallet)] += credit; creditsSent++ },
                        reply = { outcome ->
                            val earlier = outcomes.putIfAbsent(outcome.requestId, outcome)
                            if (earlier != null && earlier != outcome) conflictingReplies++
                        },
                    )
                    positions[p]++
                    if (++sinceCp == config.checkpointEvery) {             // state and offset, saved together
                        cp = proc.checkpoint(); cpOffset = positions[p]; sinceCp = 0
                    }
                    if (crashRnd.nextDouble() < config.crashChance) {      // crash: memory since the checkpoint is gone
                        proc.restore(cp); positions[p] = cpOffset; sinceCp = 0; crashes++
                    }
                }
                yield(Unit)
            }
        }
    }
    sched.run()
    val balances = LinkedHashMap<String, Long>()
    for (w in wallets) balances[w] = processors[part(w)].balances.getValue(w)
    return TransferRun(config, transfers, balances, outcomes, creditsSent, crashes, conflictingReplies)
}

/** One step of the broken design: add [delta] cents to [wallet]. A debit has a negative delta. */
data class Step(val transferId: String, val wallet: String, val delta: Long)

/** What a run of the separate-steps design produced. */
class SeparateStepsRun(
    val config: TransferConfig,
    val balances: Map<String, Long>,
    /** Transfers whose debit was written and whose credit never was: the API crashed in between. */
    val halfWritten: Int,
    /** Debits refused for lack of funds. Nothing tells the credit step, so the credit still lands. */
    val declinedDebits: Int,
    /** Steps applied a second time after a consumer crash: `balance += delta` is not idempotent. */
    val reapplied: Int,
    val crashes: Int,
) {
    val totalMoney: Long get() = balances.values.sum()
}

/**
 * The broken design (finished), for comparison. The API turns each transfer into two separate
 * writes: a debit [Step] to the source wallet's partition, then a credit [Step] to the
 * destination's. There is no request ID. Each partition's consumer applies `balance += delta` to a
 * durable table at once, refuses a debit the wallet can't cover, and commits its offset only every
 * [TransferConfig.checkpointEvery] messages, so after a crash it applies the uncommitted steps
 * again. The same faults as [runTransfers]: consumer crashes and client retries, plus an API that
 * can crash between its two writes.
 */
fun runSeparateSteps(config: TransferConfig): SeparateStepsRun {
    val crashRnd = Random(config.seed + 1)
    val wallets = (0 until config.wallets).map(::wallet)
    val transfers = transfersFor(config)
    fun part(w: String) = partitionFor(w, config.partitions)

    val logs = List(config.partitions) { ArrayList<Step>() }
    val balances = LinkedHashMap(wallets.associateWith { config.initialBalance })   // durable: survives crashes
    val positions = IntArray(config.partitions)
    var halfWritten = 0
    var declined = 0
    var reapplied = 0
    var crashes = 0
    var clientsDone = 0
    val sched = Scheduler(config.seed)

    for (c in 0 until config.clients) {
        val mine = transfers.filterIndexed { i, _ -> i % config.clients == c }
        val retry = Random(config.seed * 31 + c)
        val apiCrash = Random(config.seed * 17 + c)
        sched.spawn {
            for (t in mine) {
                val attempts = if (retry.nextDouble() < config.clientRetryChance) 2 else 1
                repeat(attempts) {
                    logs[part(t.from)] += Step(t.requestId, t.from, -t.amount)      // write 1: the debit
                    yield(Unit)
                    if (apiCrash.nextDouble() < config.apiCrashChance) {
                        halfWritten++                                               // crashed before write 2
                    } else {
                        logs[part(t.to)] += Step(t.requestId, t.to, t.amount)       // write 2: the credit
                        yield(Unit)
                    }
                }
            }
            clientsDone++
        }
    }
    for (p in 0 until config.partitions) {
        sched.spawn {
            var committed = 0
            var sinceCommit = 0
            fun allCaughtUp() = (0 until config.partitions).all { positions[it] == logs[it].size }
            while (clientsDone < config.clients || !allCaughtUp()) {
                if (positions[p] < logs[p].size) {
                    val step = logs[p][positions[p]]
                    val balance = balances.getValue(step.wallet)
                    if (step.delta < 0 && balance < -step.delta) declined++         // the credit is not told
                    else balances[step.wallet] = balance + step.delta              // written to the table at once
                    positions[p]++
                    if (++sinceCommit == config.checkpointEvery) { committed = positions[p]; sinceCommit = 0 }
                    if (crashRnd.nextDouble() < config.crashChance) {              // restart from the committed offset
                        reapplied += positions[p] - committed
                        positions[p] = committed; sinceCommit = 0; crashes++
                    }
                }
                yield(Unit)
            }
        }
    }
    sched.run()
    return SeparateStepsRun(config, balances, halfWritten, declined, reapplied, crashes)
}
