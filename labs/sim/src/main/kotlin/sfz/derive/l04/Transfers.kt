package sfz.derive.l04

import kotlin.random.Random

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
class WalletProcessor(initial: Map<String, Long>) {
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
        TODO("a Requested: dedupe by requestId, check funds, debit, send the Credit, reply; a Credit: apply once")
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
        WalletProcessor(wallets.filter { part(it) == p }.associateWith { config.initialBalance })
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
