package sfz.shard.l01

import java.util.Random

/** One payment as the shards see it: its id, its merchant and when it was created, in virtual milliseconds. */
data class Payment(val id: String, val merchant: String, val atMillis: Long)

/** Two ways to build a partition key from the same payment. Given. */
object Keys {
    /** Time first, `0000043200000#pay-17`: zero-padded, so string order is time order. */
    fun byTime(p: Payment): String = "%013d#%s".format(p.atMillis, p.id)

    /** Merchant first, then time, `M-0042#0000043200000#pay-17`: one merchant's day is one run of keys. */
    fun byMerchant(p: Payment): String = "%s#%013d#%s".format(p.merchant, p.atMillis, p.id)
}

/** A day of payments on virtual time: no clocks, no sleeping, the same list on every machine. Given. */
object Workload {
    const val HOT_MERCHANT = "M-0042"

    /**
     * [count] payments, one every [everyMillis] milliseconds from [startMillis], ids `pay-<n>` counting
     * from [firstId]. Each picks one of [merchants] merchants (`M-0000` to `M-0499` for 500) at random
     * from [seed], except that a share [hotShare] of all payments goes to [HOT_MERCHANT].
     */
    fun payments(
        count: Int,
        startMillis: Long = 0,
        everyMillis: Long = 5,
        merchants: Int = 500,
        hotShare: Double = 0.0,
        firstId: Int = 0,
        seed: Long = 7,
    ): List<Payment> {
        val rnd = Random(seed)
        return (0 until count).map { i ->
            val merchant = if (rnd.nextDouble() < hotShare) HOT_MERCHANT else "M-%04d".format(rnd.nextInt(merchants))
            Payment("pay-${firstId + i}", merchant, startMillis + i * everyMillis)
        }
    }

    /** Milliseconds from midnight to [hours]:[minutes]. */
    fun at(hours: Int, minutes: Int = 0): Long = (hours * 60L + minutes) * 60_000L
}
