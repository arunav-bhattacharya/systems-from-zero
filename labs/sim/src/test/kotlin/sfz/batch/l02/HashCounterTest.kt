package sfz.batch.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

class HashCounterTest {
    @Test
    fun `within its budget the hash counter gives exact counts in one pass`() {
        val keys = AccessLog.lines(50_000, distinctPaths = 2_000).map { field(it, 7)!! }.toList()
        val counter = HashCounter(budgetBytes = 64L shl 20)
        keys.forEach(counter::add)
        assertThat(counter.counts()).isEqualTo(keys.groupingBy { it }.eachCount().mapValues { it.value.toLong() })
    }

    @Test
    fun `memory is charged per distinct key, and a repeat costs nothing`() {
        val counter = HashCounter(budgetBytes = 10_000)
        counter.add("/v1/captures")
        assertThat(counter.bytesUsed).isEqualTo(100L + 12)              // overhead plus 12 bytes of key
        repeat(1_000) { counter.add("/v1/captures") }
        assertThat(counter.bytesUsed).isEqualTo(112)
        counter.add("/healthz")
        assertThat(counter.bytesUsed).isEqualTo(112L + 108)
        assertThat(counter.distinctKeys).isEqualTo(2)
        assertThat(counter.counts()).isEqualTo(mapOf("/v1/captures" to 1_001L, "/healthz" to 1L))
    }

    @Test
    fun `the first key past the budget throws, and the counter is left as it was`() {
        val counter = HashCounter(budgetBytes = 1_200)                   // room for ten 20-byte keys at 120 bytes each
        val keys = (0 until 11).map { "/v1/payments/pay_%03d".format(it) }
        keys.take(10).forEach(counter::add)
        assertThat(counter.bytesUsed).isEqualTo(1_200)
        counter.add(keys[3])                                             // known key: still fits
        val e = assertThrows<MemoryBudgetExceeded> { counter.add(keys[10]) }
        assertThat(e.distinctKeys).isEqualTo(10)
        assertThat(e.bytesNeeded).isEqualTo(1_320)
        assertThat(counter.distinctKeys).isEqualTo(10)
        assertThat(counter.bytesUsed).isEqualTo(1_200)
        assertThat(counter.counts()).doesNotContainKey(keys[10])
        assertThat(counter.counts()[keys[3]]).isEqualTo(2)
    }

    @Test
    fun `a million lines of a few keys fit where a thousand distinct keys do not`() {
        val few = HashCounter(budgetBytes = 2_000)
        repeat(1_000_000) { few.add(AccessLog.endpoints[it % 8]) }
        assertThat(few.counts().values.sum()).isEqualTo(1_000_000)

        val many = HashCounter(budgetBytes = 2_000)
        assertThrows<MemoryBudgetExceeded> {
            (0 until 1_000).forEach { many.add(AccessLog.path(1_000 + it)) }
        }
    }
}
