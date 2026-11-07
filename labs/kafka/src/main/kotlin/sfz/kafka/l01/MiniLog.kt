package sfz.kafka.l01

/** One record in the log. The log gives it its [offset] when you append it. */
data class LogRecord(val offset: Long, val key: String?, val value: String)

/**
 * One partition of a log, kept in memory: an ordered list of records that only grows at the end.
 *
 * The rules, which the tests check one by one:
 * - the first record gets offset 0, and every append gets the next offset: 0, 1, 2, ...
 * - nothing changes or removes a record once it is in the log;
 * - reading changes nothing, so any number of readers can read the same records.
 */
class MiniLog {
    private val records = ArrayList<LogRecord>()

    /** The offset the next append will get. In an empty log it is 0. */
    val endOffset: Long
        get() = TODO("return the offset the next record will get")

    /** Adds a record at the end of the log and returns the offset it got. */
    fun append(key: String?, value: String): Long {
        TODO("make a LogRecord with the next offset, add it to records, return its offset")
    }

    /**
     * Returns up to [max] records, starting with the record at offset [from], in offset order.
     * `from == endOffset` is allowed and returns an empty list: the reader is caught up.
     * A [from] below 0 or above [endOffset] throws [IllegalArgumentException].
     */
    fun read(from: Long, max: Int): List<LogRecord> {
        TODO("check from, then return a copy of up to max records starting at index from")
    }
}

/**
 * A reader of a [MiniLog]. All it remembers is one number, [position]: the offset of the next record it will read.
 * Readers never change the log, so two readers of the same log never affect each other.
 */
class LogReader(private val log: MiniLog, startAt: Long = 0) {
    /** The offset of the next record this reader will get. */
    var position: Long = startAt
        private set

    /** Reads up to [max] records from [position] and moves [position] just past the last record returned. */
    fun poll(max: Int): List<LogRecord> {
        TODO("read from the log at position, advance position by the number of records read")
    }

    /**
     * Moves [position] to [offset], so the next [poll] starts there. Use it to replay old records or to skip ahead.
     * An [offset] below 0 or above the log's end offset throws [IllegalArgumentException].
     */
    fun seek(offset: Long) {
        TODO("check the offset, then set position")
    }
}
