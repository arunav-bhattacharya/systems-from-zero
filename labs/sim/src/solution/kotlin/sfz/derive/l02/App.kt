package sfz.derive.l02

/*
 * Lesson derive-02 (given, nothing to change in this file): the app wired together, and the
 * read-your-writes experiment the tests and the Try it run.
 */

/** 50 accounts, acc-01 to acc-50, each opening with 1,000.00. */
val ACCOUNTS: List<String> = (1..50).map { "acc-%02d".format(it) }
const val OPENING_CENTS = 100_000L

class App(seed: Long, pollEveryMs: Long = 50) {
    val sim = Sim(seed)
    val log = Log()
    val feed = Feed(sim)
    val view = Balances(ACCOUNTS.associateWith { OPENING_CENTS })
    val processor = Processor(sim, log, view, feed, pollEveryMs).also { it.start() }

    /** The write path: append to the system of record and hand back the offset, like an LSN. */
    fun transfer(t: Transfer): Long = log.append(t)

    /** A new client copy of [account], starting from the view as it is now. */
    fun snapshot(account: String): ClientCopy {
        val r = processor.readNow(account)
        return ClientCopy(account, r.balance, r.appliedOffset)
    }
}

enum class ReadMode { NOW, AFTER_MY_WRITE }

/** One user's read of their own balance after their own transfer. */
data class ReadRecord(val writeOffset: Long, val read: Read, val askedAt: Long, val answeredAt: Long) {
    /** The view hadn't applied the user's own write yet. */
    val stale: Boolean get() = read.appliedOffset < writeOffset
    val waitMs: Long get() = answeredAt - askedAt
}

data class Outcome(val app: App, val reads: List<ReadRecord>) {
    val stale: Int get() = reads.count { it.stale }

    /** The [p]th percentile wait, nearest rank, in ms. */
    fun waitPercentile(p: Double): Long {
        val sorted = reads.map { it.waitMs }.sorted()
        return sorted[(Math.ceil(p / 100 * sorted.size).toInt() - 1).coerceIn(0, sorted.size - 1)]
    }
}

object ReadYourWrites {
    /**
     * [transfers] users each send one transfer at a random moment in one minute. The response
     * reaches the phone 5 ms later; 0 to 60 ms after that, the app reads the user's own balance,
     * either from the view as it is ([ReadMode.NOW]) or after the user's own offset
     * ([ReadMode.AFTER_MY_WRITE]).
     */
    fun run(seed: Long, mode: ReadMode, transfers: Int = 1_000): Outcome {
        val app = App(seed)
        val random = app.sim.random
        val reads = ArrayList<ReadRecord>()
        repeat(transfers) { i ->
            val at = random.nextLong(60_000)
            val from = ACCOUNTS[random.nextInt(ACCOUNTS.size)]
            val to = ACCOUNTS.filter { it != from }[random.nextInt(ACCOUNTS.size - 1)]
            val cents = 100 + random.nextLong(9_900)
            val think = random.nextLong(61)
            app.sim.at(at) {
                val offset = app.transfer(Transfer("tr-%04d".format(i), from, to, cents))
                app.sim.after(5 + think) {
                    val asked = app.sim.now
                    when (mode) {
                        ReadMode.NOW -> reads += ReadRecord(offset, app.processor.readNow(from), asked, asked)
                        ReadMode.AFTER_MY_WRITE -> app.processor.readAfter(from, offset) {
                            reads += ReadRecord(offset, it, asked, app.sim.now)
                        }
                    }
                }
            }
        }
        app.sim.runUntil(61_000)
        return Outcome(app, reads)
    }
}
