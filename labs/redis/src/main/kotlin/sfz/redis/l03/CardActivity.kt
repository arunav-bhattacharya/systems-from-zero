package sfz.redis.l03

import redis.clients.jedis.RedisClient
import java.time.LocalDate

/**
 * Which cards made at least one payment on a given day, one bitmap per day.
 *
 * Every card has a dense integer index (0, 1, 2, ...) assigned elsewhere, and bit number `cardIndex`
 * of the day's key is 1 if that card was active. A million cards cost about 125 KB per day.
 */
class CardActivity(private val redis: RedisClient, private val prefix: String) {

    /** The bitmap key for [day], for example `<prefix>active:2026-11-02`. Done for you. */
    fun keyFor(day: LocalDate): String = "${prefix}active:$day"

    /** Marks card [cardIndex] active on [day]. Returns true if it was already marked that day. Use SETBIT. */
    fun markActive(day: LocalDate, cardIndex: Long): Boolean {
        TODO("lesson 3 lab: SETBIT")
    }

    /** True if card [cardIndex] was active on [day]. Use GETBIT. */
    fun wasActive(day: LocalDate, cardIndex: Long): Boolean {
        TODO("lesson 3 lab: GETBIT")
    }

    /** How many distinct cards were active on [day]. Use BITCOUNT. */
    fun activeCount(day: LocalDate): Long {
        TODO("lesson 3 lab: BITCOUNT")
    }

    /**
     * How many cards were active on every one of [days]. Combine the days with BITOP AND into a
     * temporary key under [prefix], count it with BITCOUNT, and delete the temporary key before you return.
     */
    fun activeOnAllDays(days: List<LocalDate>): Long {
        TODO("lesson 3 lab: BITOP AND, BITCOUNT, DEL")
    }

    /** How many cards were active on at least one of [days]. Same shape as [activeOnAllDays], with BITOP OR. */
    fun activeOnAnyDay(days: List<LocalDate>): Long {
        TODO("lesson 3 lab: BITOP OR, BITCOUNT, DEL")
    }
}
