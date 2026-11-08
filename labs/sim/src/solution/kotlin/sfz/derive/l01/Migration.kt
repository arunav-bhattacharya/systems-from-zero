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

    fun startV2(view: View, batch: Int): Job {
        check(v2 == null) { "v2 is already running" }
        require(view !== v1.view) { "v2 needs its own table" }
        val job = Job("v2", log, view, batch)          // a new Job starts at position 0
        v2 = job
        return job
    }

    /** Called every minute by the world (given): v1 keeps running until it is retired, and v2 catches up. */
    fun tick(now: Long) {
        if (!v1Retired) v1.poll(now)
        v2?.poll(now)
    }

    fun shift(percent: Int): Boolean {
        require(percent in 0..100) { "percent must be 0..100, was $percent" }
        val job = v2 ?: return false                   // nothing to shift to yet
        if (job.lag > 0) return false                  // still replaying: recent days are missing
        percentOnV2 = percent                          // one assignment: the switch is atomic
        return true
    }

    fun rollback() {
        check(!v1Retired) { "v1 is retired; there is nothing to roll back to" }
        percentOnV2 = 0                                // v1 kept polling, so it is current
    }

    fun retireV1() {
        check(percentOnV2 == 100) { "move every reader to v2 first (now $percentOnV2%)" }
        v1.stop()
        v1Retired = true
    }

    fun read(merchant: String, day: Long): Answer {
        val job = if (bucketOf(merchant) < percentOnV2) v2!! else v1   // percent > 0 implies v2 exists
        return Answer(job.name, job.view.cents(merchant, day))
    }
}
