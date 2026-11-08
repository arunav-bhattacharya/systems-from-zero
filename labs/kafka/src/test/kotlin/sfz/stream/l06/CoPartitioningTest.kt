package sfz.stream.l06

import org.apache.kafka.clients.producer.internals.BuiltInPartitioner
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatCode
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import java.util.zip.CRC32

/**
 * Co-partitioning: an order meets its customer's tier only if both records sit in the same partition number,
 * because task N joins partition N of `orders` with partition N of `customer-tiers`.
 */
class CoPartitioningTest {
    private val customers = (0 until 3_000).map { "c-$it" }

    @Test
    fun `partitionFor picks the same partition as the Java producer`() {
        for (key in customers.take(500)) for (n in 1..12) {
            val producer = BuiltInPartitioner.partitionForKey(key.toByteArray(), n)
            assertThat(CoPartitioning.partitionFor(key, n)).describedAs("key $key, $n partitions").isEqualTo(producer)
        }
    }

    @Test
    fun `with 3 and 2 partitions about two keys in three land on different partition numbers`() {
        assertThat(CoPartitioning.mismatchShare(customers, 3, 2)).isBetween(0.62, 0.71)
        assertThat(CoPartitioning.mismatchShare(customers, 6, 6)).isEqualTo(0.0)
        // doubling a topic's partitions moves half of its keys: a join with an unchanged topic breaks
        assertThat(CoPartitioning.mismatchShare(customers, 6, 12)).isBetween(0.45, 0.55)
    }

    @Test
    fun `the start-up check rejects a join of topics with different partition counts`() {
        assertThatThrownBy {
            CoPartitioning.requireCoPartitioned(TierEnrichment.build(), mapOf(TierEnrichment.ORDERS to 3, TierEnrichment.TIERS to 2))
        }.isInstanceOf(IllegalStateException::class.java)
            .hasMessageContaining("orders=3").hasMessageContaining("customer-tiers=2")
    }

    @Test
    fun `the start-up check passes when the counts match`() {
        assertThatCode {
            CoPartitioning.requireCoPartitioned(TierEnrichment.build(), mapOf(TierEnrichment.ORDERS to 3, TierEnrichment.TIERS to 3))
        }.doesNotThrowAnyException()
    }

    @Test
    fun `a join against a global table needs no co-partitioning`() {
        assertThatCode {
            CoPartitioning.requireCoPartitioned(TierEnrichment.buildGlobal(), mapOf(TierEnrichment.ORDERS to 3, TierEnrichment.TIERS to 2))
        }.doesNotThrowAnyException()
    }

    @Test
    fun `same counts but another partitioner passes the check and still loses most joins`() {
        // the tiers come from a service using librdkafka's default partitioner (CRC32), the orders from a Java producer
        val crc32 = { key: String, n: Int -> (CRC32().apply { update(key.toByteArray()) }.value % n).toInt() }
        val few = customers.take(60)
        val partitions = mapOf(TierEnrichment.ORDERS to 3, TierEnrichment.TIERS to 3)
        assertThatCode { CoPartitioning.requireCoPartitioned(TierEnrichment.build(), partitions) }.doesNotThrowAnyException()

        // run the join the way Kafka Streams does: one task per partition, each reading partition N of both topics
        val misses = (0 until 3).sumOf { task ->
            val tiers = few.filter { crc32(it, 3) == task }.map { tier(it, "gold", "09:00") }
            val orders = few.filter { CoPartitioning.partitionFor(it, 3) == task }.map { order(it, "o-$it", "10:00") }
            runTopology(TierEnrichment.build(), tiers + orders).count { it.second.endsWith("tier=none") }
        }
        val expected = few.count { CoPartitioning.partitionFor(it, 3) != crc32(it, 3) }
        assertThat(misses).describedAs("orders that met no tier").isEqualTo(expected)
        assertThat(misses).isGreaterThan(few.size / 2)
    }
}
