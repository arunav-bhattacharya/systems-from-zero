package sfz.msg.l05

import org.apache.kafka.common.utils.Utils
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.random.Random

/** Your key-to-partition rule against the one inside kafka-clients. No broker needed. */
class KeyPartitionerTest {
    /** What the real producer computes for a String key: kafka-clients' own murmur2 and toPositive. */
    private fun kafkaPartition(key: String, n: Int) = Utils.toPositive(Utils.murmur2(key.toByteArray())) % n

    @Test
    fun `the given murmur2 is the same function as Kafka's (this one passes from the start)`() {
        val rnd = Random(42)
        repeat(10_000) {
            val bytes = rnd.nextBytes(rnd.nextInt(0, 40))
            assertThat(KeyPartitioner.murmur2(bytes)).isEqualTo(Utils.murmur2(bytes))
        }
    }

    @Test
    fun `toPositive clears the sign bit instead of taking the absolute value`() {
        assertThat(KeyPartitioner.toPositive(7)).isEqualTo(7)
        assertThat(KeyPartitioner.toPositive(-1)).isEqualTo(Int.MAX_VALUE)
        assertThat(KeyPartitioner.toPositive(-7)).isEqualTo(Int.MAX_VALUE - 6) // Math.abs would say 7
        assertThat(KeyPartitioner.toPositive(Int.MIN_VALUE)).isEqualTo(0)   // Math.abs would say -2147483648
    }

    @Test
    fun `the keys from lessons 3 and 4 land where the broker put them`() {
        assertThat(KeyPartitioner.partitionFor("acct-17", 3)).isEqualTo(2) // AcksDemo in lesson 4
        assertThat(KeyPartitioner.partitionFor("card-1", 3)).isEqualTo(2)  // the card-auths Try-it in lesson 3
        assertThat(KeyPartitioner.partitionFor("card-2", 3)).isEqualTo(1)
        assertThat(KeyPartitioner.partitionFor("card-3", 3)).isEqualTo(1)
    }

    @Test
    fun `partitionFor matches the producer for 10,000 keys and several partition counts`() {
        val keys = (0 until 10_000).map { "acct-$it" } + listOf("", "é", "ключ-1", "merchant:Café Sol")
        for (n in listOf(1, 3, 6, 7, 12, 50)) {
            for (key in keys) {
                assertThat(KeyPartitioner.partitionFor(key, n)).`as`("key %s, %d partitions", key, n).isEqualTo(kafkaPartition(key, n))
            }
        }
    }

    @Test
    fun `keys with a negative hash still get a partition in range`() {
        val negative = (0 until 1_000).map { "pay-$it" }.filter { Utils.murmur2(it.toByteArray()) < 0 }
        assertThat(negative).hasSizeGreaterThan(400) // about half of all hashes are negative
        for (key in negative) assertThat(KeyPartitioner.partitionFor(key, 6)).isBetween(0, 5)
    }
}
