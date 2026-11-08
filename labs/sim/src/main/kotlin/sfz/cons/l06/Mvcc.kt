package sfz.cons.l06

// Lesson cons-06 lab, part 1: one range of a distributed SQL database, as multi-version storage.
// Every write is a new version stamped with its transaction's commit timestamp. Before a transaction
// commits, its versions are intents: provisional values that say "a transaction may commit this at
// this timestamp". Your job: Range.read(). The rest of the file is provided.

/** One version of a key. An intent has [committed] false and belongs to transaction [txn]. */
data class Version(val ts: Long, val value: Long, val txn: Long?, val committed: Boolean)

/** What a read at a timestamp finds. */
sealed interface ReadResult

/** The value to return, and the timestamp of the version it came from. */
data class Value(val value: Long, val ts: Long) : ReadResult

/** A committed version the reader can't place: it may have happened before the read began, or after. */
data class Uncertain(val ts: Long) : ReadResult

/** An intent the reader can't skip: wait until transaction [txn] commits or aborts, then read again. */
data class Blocked(val txn: Long) : ReadResult

class Range(val name: String) {
    private val versions = HashMap<String, MutableList<Version>>()

    // ---------------------------------------------------------------- your part

    /**
     * Reads [key] at [readTs]. [limit] is the top of the reader's uncertainty window: a committed
     * version with a timestamp in (readTs, limit] may have been written before the read began, so the
     * reader can't simply ignore it. Without uncertainty, limit == readTs. In this order:
     *
     * 1. An intent with a timestamp at or below [limit] returns [Blocked]: once it commits, the reader
     *    would have to see it (or would not know whether to), so it must wait for the outcome.
     * 2. A committed version with readTs < ts <= limit returns [Uncertain] with the highest such ts.
     * 3. Otherwise return the newest committed version with ts <= readTs as a [Value]. Every key has
     *    one, because [load] stores a starting value below any timestamp a read will use.
     *
     * Versions above [limit] are in the future of this read whatever the clocks say: ignore them.
     */
    fun read(key: String, readTs: Long, limit: Long): ReadResult {
        TODO("cons-06: intents block, versions in the window are uncertain, else the snapshot value")
    }

    // ---------------------------------------------------------------- provided

    /** Stores the starting value of [key], committed at timestamp [ts] (by default 0). */
    fun load(key: String, value: Long, ts: Long = 0) {
        versions.getOrPut(key) { ArrayList() } += Version(ts, value, txn = null, committed = true)
    }

    /** Writes a provisional version for transaction [txn] at timestamp [ts]. */
    fun putIntent(txn: Long, key: String, value: Long, ts: Long) {
        versions.getOrPut(key) { ArrayList() } += Version(ts, value, txn, committed = false)
    }

    /** Transaction [txn] committed: its intents become ordinary committed versions at the same timestamps. */
    fun resolve(txn: Long) {
        for (list in versions.values) {
            list.replaceAll { if (it.txn == txn && !it.committed) it.copy(committed = true) else it }
        }
    }

    fun versionsOf(key: String): List<Version> = versions[key] ?: emptyList()
}
