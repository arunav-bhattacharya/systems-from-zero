package sfz.cache.l04

import redis.clients.jedis.RedisClient
import redis.clients.jedis.args.BitOP
import java.time.LocalDate
import java.util.UUID

class CardActivity(private val redis: RedisClient, private val prefix: String) {

    fun keyFor(day: LocalDate): String = "${prefix}active:$day"

    // SETBIT returns the bit's old value; the string grows to fit the offset, new bits are 0
    fun markActive(day: LocalDate, cardIndex: Long): Boolean = redis.setbit(keyFor(day), cardIndex, true)

    fun wasActive(day: LocalDate, cardIndex: Long): Boolean = redis.getbit(keyFor(day), cardIndex)

    // BITCOUNT counts the 1 bits: one per card, however many payments it made
    fun activeCount(day: LocalDate): Long = redis.bitcount(keyFor(day))

    fun activeOnAllDays(days: List<LocalDate>): Long = combine(BitOP.AND, days)

    fun activeOnAnyDay(days: List<LocalDate>): Long = combine(BitOP.OR, days)

    private fun combine(op: BitOP, days: List<LocalDate>): Long {
        val tmp = "${prefix}tmp:${UUID.randomUUID()}"            // unique, so concurrent callers don't collide
        try {
            redis.bitop(op, tmp, *days.map(::keyFor).toTypedArray())   // a missing day counts as all zeros
            return redis.bitcount(tmp)
        } finally {
            redis.del(tmp)
        }
    }
}
