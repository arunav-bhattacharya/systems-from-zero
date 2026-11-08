package sfz.cache.l03

import redis.clients.jedis.RedisClient
import redis.clients.jedis.params.ZRangeParams
import redis.clients.jedis.util.KeyValue

data class Standing(val merchant: String, val approvals: Long, val rank: Long)

class Leaderboard(private val redis: RedisClient, private val key: String) {

    // ZINCRBY creates the key and the member if they don't exist yet; scores are doubles
    fun record(merchant: String, n: Long = 1): Long = redis.zincrby(key, n.toDouble(), merchant).toLong()

    fun top(n: Int): List<Standing> = range(0, n - 1L)

    fun standingOf(merchant: String): Standing? {
        // ZREVRANK key member WITHSCORE: rank counted from the highest score, plus the score, in one call
        val hit: KeyValue<Long, Double>? = redis.zrevrankWithScore(key, merchant)
        return hit?.let { Standing(merchant, it.value.toLong(), it.key + 1) }
    }

    fun around(merchant: String, radius: Int): List<Standing> {
        val rank: Long = redis.zrevrank(key, merchant) ?: return emptyList()
        return range(maxOf(0L, rank - radius), rank + radius)   // ZRANGE clamps a stop past the end
    }

    // ZRANGE key start stop REV WITHSCORES: positions counted from the highest score, 0-based
    private fun range(start: Long, stop: Long): List<Standing> =
        redis.zrangeWithScores(key, ZRangeParams.zrangeParams(start, stop).rev())
            .mapIndexed { i, t -> Standing(t.element, t.score.toLong(), start + i + 1) }
}
