package sfz.kafka.l02

import org.apache.kafka.common.errors.OffsetOutOfRangeException

/**
 * One record. A null [value] is a tombstone: "this key is deleted" (it matters for compaction).
 * [timestampMs] is the record's create time, which time-based retention compares against.
 */
data class Rec(val offset: Long, val key: String?, val value: String?, val timestampMs: Long) {
    /** Bytes this record takes in the model: a fixed header plus the key and value characters. */
    val sizeBytes: Int
        get() = HEADER_BYTES + (key?.length ?: 0) + (value?.length ?: 0)

    companion object {
        const val HEADER_BYTES = 20
    }
}

/** One segment: a run of records that starts at [baseOffset]. On disk it is the file `<baseOffset>.log`. */
class Segment(val baseOffset: Long) {
    val records = mutableListOf<Rec>()

    val sizeBytes: Int
        get() = records.sumOf { it.sizeBytes }

    /** The newest timestamp in the segment, or -1 when it is empty. Time-based retention looks only at this. */
    val maxTimestampMs: Long
        get() = records.maxOfOrNull { it.timestampMs } ?: -1
}

/**
 * One partition stored as a list of segments, oldest first, like a partition directory on a broker.
 * The last segment is the active one: the only segment that takes appends.
 */
class SegmentedLog(val segmentBytes: Int) {
    private val segs = mutableListOf(Segment(0))

    /** All segments, oldest first. The last one is the active segment. */
    val segments: List<Segment>
        get() = segs

    val activeSegment: Segment
        get() = segs.last()

    /** The offset the next append gets. It never goes down, whatever retention deletes. */
    var endOffset: Long = 0
        private set

    /** The oldest offset you can still read: the base offset of the oldest segment. */
    val startOffset: Long
        get() = segs.first().baseOffset

    /**
     * Appends a record at [endOffset] and returns that offset.
     *
     * Roll first if you have to: when the active segment already holds records and this record would make it
     * bigger than [segmentBytes], start a new segment whose base offset is the new record's offset.
     * A record bigger than [segmentBytes] still goes in, alone, into a fresh segment.
     */
    fun append(key: String?, value: String?, timestampMs: Long): Long {
        TODO("build the Rec, roll to a new Segment(endOffset) if it does not fit, add it, bump endOffset")
    }

    /**
     * Time-based retention, the way a broker runs it every `log.retention.check.interval.ms`.
     *
     * Walk the segments from the oldest. A segment has expired when `nowMs - maxTimestampMs > retentionMs`.
     * Delete expired segments, whole, and stop at the first segment that has not expired (an empty segment
     * never expires). If that deleted every segment, the active one included, add a new empty segment
     * at [endOffset]: the log is empty, but offsets keep counting from where they were.
     *
     * Returns how many segments were deleted.
     */
    fun deleteExpired(nowMs: Long, retentionMs: Long): Int {
        TODO("drop expired segments from the front, stop at the first that is not expired, never leave zero segments")
    }

    /**
     * Returns up to [max] records starting at offset [from]. Reading below [startOffset] fails the way a
     * broker fails a fetch for an offset that retention has already deleted.
     */
    fun read(from: Long, max: Int): List<Rec> {
        if (from < startOffset || from > endOffset) {
            throw OffsetOutOfRangeException("offset $from is outside $startOffset..$endOffset")
        }
        return segs.asSequence().flatMap { it.records }.filter { it.offset >= from }.take(max).toList()
    }
}
