package sfz.repl.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Exercise 3, [shardFor]. Two shards, each a leader with one follower; the fraud dashboard reads
 * both followers. Shard 0's follower is 400 ms behind, shard 1's is 20 ms behind. Payment n is
 * authorized at n * 50 ms and captured 30 ms later.
 */
class ConsistentPrefixTest {
    private class Shards(lags: List<Long>) {
        val leaders = lags.map { Leader() }
        val followers = lags.mapIndexed { i, lag -> Replica("shard$i-follower", lag, leaders[i]) }

        fun write(now: Long, event: PaymentEvent, shardOf: (PaymentEvent, Int) -> Int) {
            leaders[shardOf(event, leaders.size)].write(now, event.paymentId, event.type)
        }

        /** The dashboard: every event the followers show at [now], from both shards. */
        fun observe(now: Long): List<PaymentEvent> =
            followers.flatMap { f -> f.entriesUpTo(f.position(now)).map { PaymentEvent(it.key, it.value) } }
    }

    /** How many dashboard refreshes showed a captured payment whose authorization was not there. */
    private fun capturesWithoutAuthorization(shardOf: (PaymentEvent, Int) -> Int): Int {
        val shards = Shards(listOf(400L, 20L))
        for (n in 1..20) {
            shards.write(n * 50L, PaymentEvent("pay-$n", "authorized"), shardOf)
            shards.write(n * 50L + 30, PaymentEvent("pay-$n", "captured"), shardOf)
        }
        var anomalies = 0
        for (now in 0L..2_000L step 10) {
            val seen = shards.observe(now)
            val authorized = seen.filter { it.type == "authorized" }.map { it.paymentId }.toSet()
            anomalies += seen.count { it.type == "captured" && it.paymentId !in authorized }
        }
        return anomalies
    }

    @Test
    fun `a shard per event type shows captures before their authorizations`() {
        assertThat(capturesWithoutAuthorization(::shardByType)).isEqualTo(700)
    }

    @Test
    fun `a shard per payment keeps each payment's events in one log, so they appear in order`() {
        assertThat(capturesWithoutAuthorization(::shardFor)).isEqualTo(0)
    }

    @Test
    fun `shardFor depends only on the payment and stays in range`() {
        for (n in 1..500) {
            val id = "pay-$n"
            val s = shardFor(PaymentEvent(id, "authorized"), 4)
            assertThat(s).isBetween(0, 3)
            assertThat(shardFor(PaymentEvent(id, "captured"), 4)).isEqualTo(s)
            assertThat(shardFor(PaymentEvent(id, "refunded"), 4)).isEqualTo(s)
        }
        val used = (1..500).map { shardFor(PaymentEvent("pay-$it", "authorized"), 4) }.toSet()
        assertThat(used).containsExactlyInAnyOrder(0, 1, 2, 3)   // and it spreads payments over every shard
    }
}
