package sfz.cache.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import redis.clients.jedis.params.ScanParams
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.time.LocalDate
import java.util.concurrent.TimeUnit

@ExtendWith(WithRedis::class)
@Timeout(10, unit = TimeUnit.SECONDS)
class CardActivityTest {
    private val redis = TestRedis.jedis
    private val mon = LocalDate.of(2026, 11, 2)
    private val tue = mon.plusDays(1)
    private val wed = mon.plusDays(2)

    @Test
    fun `markActive sets one bit and says whether it was already set`(keys: KeySpace) {
        val activity = CardActivity(redis, keys.prefix)

        assertThat(activity.markActive(mon, 7)).isFalse()
        assertThat(activity.markActive(mon, 7)).isTrue()

        assertThat(activity.wasActive(mon, 7)).isTrue()
        assertThat(activity.wasActive(mon, 8)).isFalse()
        assertThat(activity.wasActive(tue, 7)).isFalse()
        assertThat(redis.getbit(activity.keyFor(mon), 7)).isTrue()
    }

    @Test
    fun `activeCount counts cards, not payments`(keys: KeySpace) {
        val activity = CardActivity(redis, keys.prefix)
        repeat(5) { activity.markActive(mon, 42) }       // one card, five payments
        activity.markActive(mon, 7)
        activity.markActive(mon, 1_000)

        assertThat(activity.activeCount(mon)).isEqualTo(3)
        assertThat(activity.activeCount(tue)).isZero()   // a day with no key counts as zero
    }

    @Test
    fun `activeOnAllDays counts only the cards active on every day`(keys: KeySpace) {
        val activity = CardActivity(redis, keys.prefix)
        for (card in listOf(1L, 2L, 3L, 4L)) activity.markActive(mon, card)
        for (card in listOf(2L, 3L, 4L, 5L)) activity.markActive(tue, card)
        for (card in listOf(3L, 4L, 6L)) activity.markActive(wed, card)

        assertThat(activity.activeOnAllDays(listOf(mon, tue))).isEqualTo(3)
        assertThat(activity.activeOnAllDays(listOf(mon, tue, wed))).isEqualTo(2)
    }

    @Test
    fun `activeOnAnyDay counts each card once across the days`(keys: KeySpace) {
        val activity = CardActivity(redis, keys.prefix)
        for (card in listOf(1L, 2L, 3L, 4L)) activity.markActive(mon, card)
        for (card in listOf(2L, 3L, 4L, 5L)) activity.markActive(tue, card)
        for (card in listOf(3L, 4L, 6L)) activity.markActive(wed, card)

        assertThat(activity.activeOnAnyDay(listOf(mon, tue, wed))).isEqualTo(6)
    }

    @Test
    fun `combining days leaves no temporary keys behind`(keys: KeySpace) {
        val activity = CardActivity(redis, keys.prefix)
        activity.markActive(mon, 1)
        activity.markActive(tue, 1)

        activity.activeOnAllDays(listOf(mon, tue))
        activity.activeOnAnyDay(listOf(mon, tue))

        val left = redis.scan(ScanParams.SCAN_POINTER_START, ScanParams().match("${keys.prefix}*").count(1_000)).result
        assertThat(left).containsExactlyInAnyOrder(activity.keyFor(mon), activity.keyFor(tue))
    }

    @Test
    fun `a bitmap for a million cards takes 125,000 bytes`(keys: KeySpace) {
        val activity = CardActivity(redis, keys.prefix)

        activity.markActive(mon, 999_999)                // the highest card index sets the size

        assertThat(redis.strlen(activity.keyFor(mon))).isEqualTo(125_000)
        assertThat(activity.activeCount(mon)).isEqualTo(1)
    }
}
