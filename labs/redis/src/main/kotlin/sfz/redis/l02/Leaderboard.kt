package sfz.redis.l02

import redis.clients.jedis.RedisClient

/** One merchant's place on the board. [rank] 1 is the top. */
data class Standing(val merchant: String, val approvals: Long, val rank: Long)

/**
 * Today's merchants ranked by approved payments, kept in one sorted set at [key]:
 * the member is the merchant id, the score is its number of approved payments.
 *
 * Redis ranks are 0-based and count from the lowest score. This class shows 1-based ranks
 * counted from the highest score, the way a leaderboard reads.
 */
class Leaderboard(private val redis: RedisClient, private val key: String) {

    /** Adds [n] approved payments for [merchant] (a negative [n] records reversals). Returns its new total. Use ZINCRBY. */
    fun record(merchant: String, n: Long = 1): Long {
        TODO("lesson 2 lab: ZINCRBY")
    }

    /**
     * The top [n] merchants, highest total first, with ranks 1..n.
     * Use one ZRANGE with REV and WITHSCORES (Jedis: `zrangeWithScores(key, ZRangeParams.zrangeParams(0, n - 1).rev())`).
     * Merchants with equal totals come out the way Redis orders them under REV: reverse member order.
     */
    fun top(n: Int): List<Standing> {
        TODO("lesson 2 lab: ZRANGE ... REV WITHSCORES")
    }

    /** Where [merchant] stands, or null if it has no entry. One round trip: ZREVRANK with WITHSCORE (Redis 7.2+). */
    fun standingOf(merchant: String): Standing? {
        TODO("lesson 2 lab: ZREVRANK ... WITHSCORE")
    }

    /**
     * [merchant] and up to [radius] merchants above and below it, highest first. Empty if [merchant] has no entry.
     * Near the top there are fewer merchants above, so the list is shorter.
     */
    fun around(merchant: String, radius: Int): List<Standing> {
        TODO("lesson 2 lab: ZREVRANK, then a ZRANGE ... REV around it")
    }
}
