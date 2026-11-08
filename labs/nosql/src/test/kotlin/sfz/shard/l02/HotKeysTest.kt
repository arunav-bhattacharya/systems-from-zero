package sfz.shard.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class HotKeysTest {
    private val second = 1_794_045_600_000L // 2026-11-07T10:00:00Z, in epoch millis

    @Test
    fun `a key with more than the limit in one second is hot, at the limit it is not`() {
        val d = HotKeyDetector(1_000)
        repeat(1_001) { d.record("MERCH#M-0042", second + it % 1_000) }
        repeat(1_000) { d.record("MERCH#M-0043", second + it % 1_000) }
        assertThat(d.hotKeys()).isEqualTo(mapOf("MERCH#M-0042" to 1_001))
    }

    @Test
    fun `the same requests spread over two seconds are not hot`() {
        val d = HotKeyDetector(1_000)
        // 1,500 requests, 750 in each of two seconds
        repeat(1_500) { d.record("MERCH#M-0042", second + it * 1_000L / 750) }
        assertThat(d.hotKeys()).isEmpty()
    }

    @Test
    fun `hotKeys reports the busiest second`() {
        val d = HotKeyDetector(1_000)
        repeat(1_200) { d.record("MERCH#M-0042", second + 5_000) }
        repeat(1_100) { d.record("MERCH#M-0042", second + 6_999) }
        repeat(300) { d.record("MERCH#M-0042", second + 7_000) }
        assertThat(d.hotKeys()).containsExactlyEntriesOf(mapOf("MERCH#M-0042" to 1_200))
    }

    @Test
    fun `shardKey is stable for a payment and spreads payments evenly`() {
        assertThat(WriteSharding.shardKey("M-0042", "pay-81723", 10)).isEqualTo("MERCH#M-0042#1")
        assertThat(WriteSharding.shardKey("M-0042", "pay-81723", 10)).isEqualTo(WriteSharding.shardKey("M-0042", "pay-81723", 10))
        val perShard = (0 until 10_000).groupingBy { WriteSharding.shardKey("M-0042", "pay-$it", 10) }.eachCount()
        assertThat(perShard.keys).containsExactlyInAnyOrderElementsOf(WriteSharding.allShardKeys("M-0042", 10))
        assertThat(perShard.values).allMatch { it in 900..1_100 }
    }

    @Test
    fun `sharding one hot merchant over ten keys brings every key under the limit`() {
        // Black Friday: 4,000 payments for M-0042 in one second, plus a few other merchants
        val payments = (0 until 4_000).map { "M-0042" to "pay-$it" } + (4_000 until 6_000).map { "M-%04d".format(100 + it % 50) to "pay-$it" }

        val plain = HotKeyDetector(1_000)
        payments.forEach { (m, p) -> plain.record(WriteSharding.merchantKey(m), second + 500) }
        assertThat(plain.hotKeys()).isEqualTo(mapOf("MERCH#M-0042" to 4_000))

        val sharded = HotKeyDetector(1_000)
        payments.forEach { (m, p) -> sharded.record(WriteSharding.shardKey(m, p, 10), second + 500) }
        assertThat(sharded.hotKeys()).isEmpty()
    }
}
