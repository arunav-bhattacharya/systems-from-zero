package sfz.msg.l03

import org.apache.kafka.common.errors.OffsetOutOfRangeException
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test

/** The segment model. No broker needed. */
class SegmentedLogTest {
    private val hour = 3_600_000L
    private val now = 100 * hour

    // every record is 30 bytes in the model: 20 header + "k" + a 9-character value
    private fun SegmentedLog.add(n: Int, timestampMs: Long) = repeat(n) { append("k", "payment-$it".padEnd(9, '-').take(9), timestampMs) }

    @Test
    fun `offsets keep counting across segments and each segment is named by its first offset`() {
        val log = SegmentedLog(segmentBytes = 100) // three 30-byte records fit, the fourth rolls
        log.add(10, now)
        assertThat(log.segments.map { it.baseOffset }).containsExactly(0L, 3L, 6L, 9L)
        assertThat(log.segments.map { it.records.size }).containsExactly(3, 3, 3, 1)
        assertThat(log.endOffset).isEqualTo(10)
        assertThat(log.activeSegment.baseOffset).isEqualTo(9)
    }

    @Test
    fun `a segment rolls only when the next record would not fit`() {
        val log = SegmentedLog(segmentBytes = 90) // exactly three records fit
        log.add(3, now)
        assertThat(log.segments).hasSize(1)
        log.add(1, now)
        assertThat(log.segments.map { it.baseOffset }).containsExactly(0L, 3L)
    }

    @Test
    fun `a record bigger than a segment still goes in, alone`() {
        val log = SegmentedLog(segmentBytes = 50)
        log.append("k", "x".repeat(100), now)
        log.append("k", "x".repeat(100), now)
        assertThat(log.segments.map { it.records.size }).containsExactly(1, 1)
    }

    @Test
    fun `retention deletes whole segments, so expired records that share a segment with new ones survive`() {
        val log = SegmentedLog(segmentBytes = 100)
        log.add(8, now - 5 * hour) // offsets 0..7 are old
        log.add(2, now)            // offsets 8..9 are new
        // segments: [0,1,2] old, [3,4,5] old, [6,7,8] mixed, [9] new

        val deleted = log.deleteExpired(nowMs = now, retentionMs = 2 * hour)

        assertThat(deleted).isEqualTo(2)
        assertThat(log.startOffset).isEqualTo(6) // the earliest offset jumps by whole segments: 0 -> 6
        assertThat(log.read(6, 10).map { it.offset }).containsExactly(6L, 7L, 8L, 9L)
        // 6 and 7 are past retention but still readable: their segment's newest record is young
        assertThat(log.read(6, 2).map { it.timestampMs }).containsOnly(now - 5 * hour)
    }

    @Test
    fun `retention stops at the first segment that has not expired`() {
        val log = SegmentedLog(segmentBytes = 100)
        log.add(3, now - 5 * hour) // [0,1,2] old
        log.add(3, now)            // [3,4,5] new
        log.add(3, now - 5 * hour) // [6,7,8] old again: a producer sent old timestamps
        log.add(1, now)            // [9]

        assertThat(log.deleteExpired(nowMs = now, retentionMs = 2 * hour)).isEqualTo(1)
        assertThat(log.segments.map { it.baseOffset }).containsExactly(3L, 6L, 9L)
    }

    @Test
    fun `nothing expires while every segment holds a young record`() {
        val log = SegmentedLog(segmentBytes = 100)
        log.add(10, now)
        assertThat(log.deleteExpired(nowMs = now, retentionMs = 2 * hour)).isEqualTo(0)
        assertThat(log.startOffset).isEqualTo(0)
        assertThat(SegmentedLog(100).deleteExpired(nowMs = now, retentionMs = 0)).isEqualTo(0)
    }

    @Test
    fun `when everything has expired the log is empty but offsets keep counting`() {
        val log = SegmentedLog(segmentBytes = 100)
        log.add(10, now - 5 * hour)

        assertThat(log.deleteExpired(nowMs = now, retentionMs = 2 * hour)).isEqualTo(4)

        assertThat(log.segments).hasSize(1)
        assertThat(log.startOffset).isEqualTo(10)
        assertThat(log.endOffset).isEqualTo(10)
        assertThat(log.read(10, 5)).isEmpty()
        assertThat(log.append("k", "new", now)).isEqualTo(10) // never back to 0
    }

    @Test
    fun `a read below the start offset fails like a fetch for a deleted offset`() {
        val log = SegmentedLog(segmentBytes = 100)
        log.add(8, now - 5 * hour)
        log.add(2, now)
        log.deleteExpired(nowMs = now, retentionMs = 2 * hour)
        assertThatThrownBy { log.read(0, 1) }.isInstanceOf(OffsetOutOfRangeException::class.java)
    }
}
