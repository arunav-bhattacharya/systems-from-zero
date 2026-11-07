package sfz.redis.l05

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

/** A slow, in-memory stand-in for the merchant table, with a counter of how often it was queried. */
class FakeMerchantRepository(private val delayMillis: Long = 50) : MerchantRepository {
    val rows = ConcurrentHashMap<String, Merchant>()
    private val counter = AtomicInteger()

    /** How many times [find] was called. */
    val calls: Int get() = counter.get()

    override fun find(id: String): Merchant? {
        counter.incrementAndGet()
        Thread.sleep(delayMillis)                     // a database round trip
        return rows[id]
    }

    fun add(vararg merchants: Merchant) = merchants.forEach { rows[it.id()] = it }
}
