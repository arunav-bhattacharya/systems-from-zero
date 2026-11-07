package sfz.redis.support

import redis.clients.jedis.params.ScanParams
import java.util.concurrent.atomic.AtomicLong

/**
 * A key prefix that belongs to one test, so tests never see each other's keys and
 * nobody has to FLUSHALL the shared server.
 *
 * Most tests get one as a parameter through [WithRedis]. Call [fresh] for one of your own.
 */
class KeySpace(val prefix: String) {
    /** The full key name for [name] inside this space. */
    fun key(name: String): String = prefix + name

    /** Shorthand for [key]: `keys("board")`. */
    operator fun invoke(name: String): String = key(name)

    /** Deletes every key under this prefix with SCAN and UNLINK (never KEYS). Returns how many went. */
    fun clear(): Long {
        val redis = TestRedis.jedis
        val params = ScanParams().match("$prefix*").count(500)
        var cursor = ScanParams.SCAN_POINTER_START
        var deleted = 0L
        do {
            val page = redis.scan(cursor, params)
            if (page.result.isNotEmpty()) deleted += redis.unlink(*page.result.toTypedArray())
            cursor = page.cursor
        } while (cursor != ScanParams.SCAN_POINTER_START)
        return deleted
    }

    override fun toString() = "KeySpace($prefix)"

    companion object {
        private val counter = AtomicLong()

        /** A new, never-used prefix: `t:<label>:<n>:`. */
        fun fresh(label: String = "test"): KeySpace {
            val clean = label.replace(Regex("[^A-Za-z0-9]+"), "-").trim('-').take(40).ifEmpty { "test" }
            return KeySpace("t:$clean:${counter.incrementAndGet()}:")
        }
    }
}
