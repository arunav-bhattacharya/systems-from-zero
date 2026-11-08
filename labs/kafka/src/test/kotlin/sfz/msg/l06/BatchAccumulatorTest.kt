package sfz.msg.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** The accumulator model. Time is in milliseconds. No broker needed. */
class BatchAccumulatorTest {
    private val batchSize = 16_384 // Kafka's default batch.size

    @Test
    fun `with linger 0 a record may leave as soon as it is appended`() {
        val acc = BatchAccumulator(batchSize, 0)
        acc.append(0, 100, 1_000)
        val out = acc.drain(1_000)
        assertThat(out).hasSize(1)
        assertThat(out[0].records).isEqualTo(1)
        assertThat(acc.waiting()).isZero()
    }

    @Test
    fun `with linger 5 a batch waits 5 ms and collects what arrives meanwhile`() {
        val acc = BatchAccumulator(batchSize, 5)
        for (t in 0L..4L) acc.append(0, 100, t)
        assertThat(acc.drain(4)).isEmpty()           // 4 ms old: still lingering
        val out = acc.drain(5)                        // 5 ms old: may leave
        assertThat(out.single().records).isEqualTo(5)
        assertThat(out.single().bytes).isEqualTo(500)
    }

    @Test
    fun `a full batch leaves at once, without waiting for linger`() {
        val acc = BatchAccumulator(batchSize, 50)
        repeat(17) { acc.append(0, 1_000, 0) }       // 16 fit in 16,384 bytes; the 17th does not
        val out = acc.drain(0)
        assertThat(out.single().records).isEqualTo(16)
        assertThat(out.single().closed).isTrue()
        assertThat(acc.waiting()).isEqualTo(1)        // the 17th waits in a new batch
        assertThat(acc.drain(49)).isEmpty()
        assertThat(acc.drain(50).single().records).isEqualTo(1)
    }

    @Test
    fun `each partition fills its own batches`() {
        val acc = BatchAccumulator(batchSize, 5)
        acc.append(0, 100, 0)
        acc.append(1, 100, 1)
        acc.append(0, 100, 2)
        val out = acc.drain(5)
        assertThat(out.map { it.partition to it.records }).containsExactly(0 to 2) // partition 1's batch is 4 ms old
        assertThat(acc.drain(6).map { it.partition to it.records }).containsExactly(1 to 1)
    }

    @Test
    fun `a record bigger than batch size gets a batch of its own`() {
        val acc = BatchAccumulator(batchSize, 50)
        acc.append(0, 100, 0)
        val big = acc.append(0, 40_000, 0)
        assertThat(big.records).isEqualTo(1)
        assertThat(big.closed).isTrue()
        val out = acc.drain(0)
        assertThat(out.map { it.records }).containsExactly(1, 1) // the small one was closed when the big one did not fit
    }

    @Test
    fun `batches of one partition leave in order, so a lingering batch holds back nothing older`() {
        val acc = BatchAccumulator(batchSize, 10)
        repeat(20) { acc.append(0, 1_000, 0) } // one full batch of 16, then 4 records in an open batch
        acc.append(0, 1_000, 3)
        assertThat(acc.drain(3).map { it.records }).containsExactly(16)
        assertThat(acc.drain(10).map { it.records }).containsExactly(5)
    }

    /** One 100-byte record every millisecond for one second, and the sender drains every millisecond. */
    private fun trickle(lingerMs: Long): Double {
        val acc = BatchAccumulator(batchSize, lingerMs)
        val sent = mutableListOf<Batch>()
        for (t in 0L until 1_000L) {
            acc.append(0, 100, t)
            sent += acc.drain(t)
        }
        sent += acc.drain(Long.MAX_VALUE / 2)
        return sent.sumOf { it.records }.toDouble() / sent.size
    }

    @Test
    fun `at 1,000 records a second, records per batch grow with linger ms`() {
        assertThat(trickle(0)).isEqualTo(1.0)
        assertThat(trickle(5)).isBetween(5.9, 6.0)   // a batch collects the records of 6 milliseconds
        assertThat(trickle(50)).isBetween(50.0, 51.0)
    }

    @Test
    fun `a burst fills batches to batch size and only the last one lingers`() {
        val acc = BatchAccumulator(batchSize, 5)
        repeat(1_000) { acc.append(0, 100, 0) } // 163 records of 100 bytes fit in 16,384 bytes
        val now = acc.drain(0)
        assertThat(now.map { it.records }).containsOnly(163).hasSize(6)
        assertThat(acc.drain(5).single().records).isEqualTo(1_000 - 6 * 163)
    }
}
