package sfz.derive.l01

/** One answer to a dashboard read, and which version's table it came from ("v1" or "v2"). */
data class Answer(val version: String, val cents: Long)

/**
 * Kreps's reprocessing recipe for one derived table, with a gradual cutover.
 *
 * 1. Keep the whole input in the log (the [EventLog] already does).
 * 2. Start a second job, v2, from offset 0, writing to a new table, while v1 keeps serving.
 * 3. When v2 has caught up, move readers to it: a share of merchants at a time, with rollback.
 * 4. When everyone is on v2, stop v1 and drop its table.
 */
class Migration(private val log: EventLog, val v1: Job) {
    /** The new job, once [startV2] has run. */
    var v2: Job? = null
        private set

    /** Merchants whose [bucketOf] is below this number read from v2; everyone else reads v1. */
    var percentOnV2: Int = 0
        private set

    var v1Retired: Boolean = false
        private set

    /**
     * Step 2. Create v2 as a new [Job] named "v2" that reads [log] from the beginning and writes
     * [view], a new, empty table (never v1's). Store it in [v2] and return it. Starting twice is
     * a mistake: throw IllegalStateException.
     */
    fun startV2(view: View, batch: Int): Job {
        TODO("create the v2 job reading from offset 0")
    }

    /** Called every minute by the world (given): v1 keeps running until it is retired, and v2 catches up. */
    fun tick(now: Long) {
        if (!v1Retired) v1.poll(now)
        v2?.poll(now)
    }

    /**
     * Step 3. Send [percent] (0 to 100) of merchants to v2. Refuse, return false and change
     * nothing, when v2 hasn't started or still has records to read ([Job.lag] above 0): a reader
     * moved early would see a table that is missing the recent days. Otherwise set
     * [percentOnV2] and return true.
     */
    fun shift(percent: Int): Boolean {
        require(percent in 0..100) { "percent must be 0..100, was $percent" }
        TODO("refuse while v2 is missing or behind; otherwise set percentOnV2")
    }

    /**
     * Send every reader back to v1. This works because v1 never stopped: it is still current.
     * After [retireV1] there is nothing to go back to: throw IllegalStateException.
     */
    fun rollback() {
        TODO("everyone back on v1, unless v1 is retired")
    }

    /**
     * Step 4. Only when every reader is on v2 (100%); otherwise throw IllegalStateException.
     * Stop v1 (which drops its table) and remember that it is retired.
     */
    fun retireV1() {
        TODO("stop v1 once everyone reads v2")
    }

    /**
     * One merchant's revenue for one day. A merchant whose [bucketOf] is below [percentOnV2]
     * reads v2's table; every other merchant reads v1's. The whole answer comes from one table,
     * and [Answer.version] names it.
     */
    fun read(merchant: String, day: Long): Answer {
        TODO("pick the version for this merchant and read its table")
    }
}
