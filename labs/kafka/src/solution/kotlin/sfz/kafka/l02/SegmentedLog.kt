package sfz.kafka.l02

import org.apache.kafka.common.errors.OffsetOutOfRangeException

data class Rec(val offset: Long, val key: String?, val value: String?, val timestampMs: Long) {
    val sizeBytes: Int
        get() = HEADER_BYTES + (key?.length ?: 0) + (value?.length ?: 0)

    companion object {
        const val HEADER_BYTES = 20
    }
}

class Segment(val baseOffset: Long) {
    val records = mutableListOf<Rec>()

    val sizeBytes: Int
        get() = records.sumOf { it.sizeBytes }

    val maxTimestampMs: Long
        get() = records.maxOfOrNull { it.timestampMs } ?: -1
}

class SegmentedLog(val segmentBytes: Int) {
    private val segs = mutableListOf(Segment(0))

    val segments: List<Segment>
        get() = segs

    val activeSegment: Segment
        get() = segs.last()

    var endOffset: Long = 0
        private set

    val startOffset: Long
        get() = segs.first().baseOffset

    fun append(key: String?, value: String?, timestampMs: Long): Long {
        val rec = Rec(endOffset, key, value, timestampMs)
        // roll: close the active segment when this record would push it past segmentBytes
        if (activeSegment.records.isNotEmpty() && activeSegment.sizeBytes + rec.sizeBytes > segmentBytes) {
            segs += Segment(baseOffset = rec.offset) // the new file is named after its first offset
        }
        activeSegment.records += rec
        endOffset++
        return rec.offset
    }

    fun deleteExpired(nowMs: Long, retentionMs: Long): Int {
        var deleted = 0
        // oldest first; the first segment that has not expired stops the sweep
        while (deleted < segs.size) {
            val seg = segs[deleted]
            val expired = seg.records.isNotEmpty() && nowMs - seg.maxTimestampMs > retentionMs
            if (!expired) break
            deleted++
        }
        if (deleted == 0) return 0
        repeat(deleted) { segs.removeAt(0) } // whole segments go; never single records
        // everything expired, the active segment too: Kafka rolls a new, empty one first
        if (segs.isEmpty()) segs += Segment(baseOffset = endOffset)
        return deleted
    }

    fun read(from: Long, max: Int): List<Rec> {
        if (from < startOffset || from > endOffset) {
            throw OffsetOutOfRangeException("offset $from is outside $startOffset..$endOffset")
        }
        return segs.asSequence().flatMap { it.records }.filter { it.offset >= from }.take(max).toList()
    }
}
