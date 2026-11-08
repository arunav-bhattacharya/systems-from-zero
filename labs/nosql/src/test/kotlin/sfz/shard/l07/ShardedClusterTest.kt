package sfz.shard.l07

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class ShardedClusterTest {
    private val shards = listOf("shard-a", "shard-b", "shard-c")
    private val start = 1_794_009_600_000L // 2026-11-07T00:00:00Z

    /** Payment i: one second after payment i - 1; every fifth one is merchant M-0042's. */
    private fun payment(i: Int) = Payment(
        paymentId = "pay-${100_000 + i}",
        merchantId = if (i % 5 == 0) "M-0042" else "M-${1_000 + i % 400}",
        accountId = "A-${1_001 + i % 500}",
        createdAtMillis = start + i * 1_000L,
    )

    private fun cluster(key: ShardKeyPattern, payments: Int): ShardedCluster =
        ShardedCluster(key, shards).also { c -> (0 until payments).forEach { c.insert(payment(it)) } }

    @Test
    fun `keyOf builds the key each pattern describes`() {
        val p = payment(0)
        assertThat(ShardKeyPattern.RANGED_CREATED_AT.keyOf(p)).isEqualTo(Key.of(start))
        assertThat(ShardKeyPattern.HASHED_PAYMENT_ID.keyOf(p)).isEqualTo(Key.of(hash64("pay-100000")))
        assertThat(ShardKeyPattern.HASHED_MERCHANT.keyOf(p)).isEqualTo(Key.of(hash64("M-0042")))
        assertThat(ShardKeyPattern.HASHED_MERCHANT_THEN_TIME.keyOf(p)).isEqualTo(Key.of(hash64("M-0042"), start))
    }

    @Test
    fun `chunkFor finds the chunk whose range holds the key`() {
        val c = ShardedCluster(ShardKeyPattern.HASHED_PAYMENT_ID, shards) // one chunk per shard, as in MongoDB 8.0+
        assertThat(c.chunks).hasSize(3)
        assertThat(c.chunkFor(Key.of(Long.MIN_VALUE)).shard).isEqualTo("shard-a")
        assertThat(c.chunkFor(Key.of(0)).shard).isEqualTo("shard-b")
        assertThat(c.chunkFor(Key.of(Long.MAX_VALUE)).shard).isEqualTo("shard-c")
    }

    @Test
    fun `a hashed _id spreads inserts over every shard`() {
        val c = ShardedCluster(ShardKeyPattern.HASHED_PAYMENT_ID, shards)
        val perShard = (0 until 30_000).groupingBy { c.insert(payment(it)) }.eachCount()
        assertThat(perShard.keys).containsExactlyInAnyOrderElementsOf(shards)
        assertThat(perShard.values).allMatch { it in 9_500..10_500 }
        assertThat(c.chunks.values.sumOf { it.keys.size }).isEqualTo(30_000)
    }

    @Test
    fun `an increasing createdAt sends every insert to the chunk that ends at MaxKey`() {
        val c = cluster(ShardKeyPattern.RANGED_CREATED_AT, 5_000)
        assertThat(c.chunks).hasSize(1) // inserts never split a chunk
        assertThat(c.docsOn("shard-a")).isEqualTo(5_000)

        c.balance() // the balancer spreads the old data out...
        val hot = c.lastChunk()
        val before = hot.keys.size
        // ...but the next 1,000 payments all go to one chunk on one shard
        val targets = (5_000 until 6_000).map { c.insert(payment(it)) }.toSet()
        assertThat(targets).containsExactly(hot.shard)
        assertThat(hot.max).isEqualTo(Key.MAX)
        assertThat(hot.keys.size - before).isEqualTo(1_000)
    }

    @Test
    fun `splitLargeChunks cuts chunk-size pieces between different keys`() {
        val c = cluster(ShardKeyPattern.RANGED_CREATED_AT, 2_500) // 2.5 MB in one chunk; the chunk size is 1 MB
        c.splitLargeChunks()
        assertThat(c.chunks.values.map { it.keys.size }).containsExactly(1_000, 1_000, 500)
        assertThat(c.chunks.values.map { it.min }).containsExactly(Key.MIN, Key.of(start + 1_000_000), Key.of(start + 2_000_000))
        assertThat(c.lastChunk().max).isEqualTo(Key.MAX)
        assertThat(c.chunks.values).allMatch { it.shard == "shard-a" && !it.jumbo }
    }

    @Test
    fun `a balancer round moves one chunk-size range from the fullest shard to the emptiest`() {
        val c = cluster(ShardKeyPattern.RANGED_CREATED_AT, 20_000) // 20 MB, all on shard-a
        val first = c.balancerRound()
        // three shards: a shard takes part in one migration per round, so at most one move.
        // shard-b and shard-c tie at 0 bytes; shard-b is listed first, so shard-c counts as emptier.
        assertThat(first).containsExactly(Migration(Key.MIN, Key.of(start + 1_000_000), "shard-a", "shard-c", 1_000_000))
        assertThat(c.chunks).hasSize(20)
        assertThat(c.balancerRound()).containsExactly(
            Migration(Key.of(start + 1_000_000), Key.of(start + 2_000_000), "shard-a", "shard-b", 1_000_000))
    }

    @Test
    fun `the balancer stops once shards differ by less than three chunk sizes`() {
        val c = cluster(ShardKeyPattern.RANGED_CREATED_AT, 20_000)
        val moves = c.balance()
        assertThat(moves).hasSize(12)
        assertThat(shards.map { c.bytesOn(it) }).containsExactly(8_000_000, 6_000_000, 6_000_000)
        assertThat(c.balancerRound()).isEmpty()
    }

    @Test
    fun `mongos targets one shard when the filter has the shard key, and asks them all when it doesn't`() {
        val byId = cluster(ShardKeyPattern.HASHED_PAYMENT_ID, 3_000)
        assertThat(byId.route(PaymentQuery(paymentId = "pay-101723")).stage).isEqualTo("SINGLE_SHARD")
        val dashboard = PaymentQuery(merchantId = "M-0042", fromMillis = start, toMillis = start + 3_600_000)
        assertThat(byId.route(dashboard).shards).containsExactlyInAnyOrderElementsOf(shards)
        assertThat(byId.route(dashboard).stage).isEqualTo("SHARD_MERGE")

        val byMerchant = cluster(ShardKeyPattern.HASHED_MERCHANT_THEN_TIME, 3_000)
        assertThat(byMerchant.route(dashboard).stage).isEqualTo("SINGLE_SHARD")
        assertThat(byMerchant.route(PaymentQuery(paymentId = "pay-101723")).shards).containsExactlyInAnyOrderElementsOf(shards)
    }

    @Test
    fun `a merchant with a fifth of all payments becomes a jumbo chunk the balancer can't move`() {
        val c = cluster(ShardKeyPattern.HASHED_MERCHANT, 20_000)
        val m0042 = Key.of(hash64("M-0042"))
        val home = c.chunkFor(m0042).shard
        val moves = c.balance()

        val jumbo = c.chunks.values.filter { it.jumbo }
        assertThat(jumbo).hasSize(1)
        assertThat(jumbo.single().keys).hasSize(4_000).allMatch { it == m0042 } // 4 MB under one key value
        assertThat(jumbo.single().shard).isEqualTo(home)
        assertThat(moves).noneMatch { m0042 >= it.min && m0042 < it.max }
        assertThat(c.chunks.values.filter { !it.jumbo }).allMatch { it.keys.size <= 1_000 }
    }

    @Test
    fun `adding createdAt to the key lets the busy merchant split and spread`() {
        val c = cluster(ShardKeyPattern.HASHED_MERCHANT_THEN_TIME, 20_000)
        c.balance()
        assertThat(c.chunks.values).noneMatch { it.jumbo }
        val h = hash64("M-0042")
        val holding = c.chunks.values.filter { ch -> ch.keys.any { it.parts.first() == h } }
        assertThat(holding.size).isGreaterThanOrEqualTo(4)
        assertThat(shards.maxOf { c.bytesOn(it) } - shards.minOf { c.bytesOn(it) }).isLessThan(3_000_000)
    }
}
