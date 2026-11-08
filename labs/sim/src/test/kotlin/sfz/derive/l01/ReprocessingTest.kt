package sfz.derive.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** What a replay must produce: the same table a batch job would compute, by event time. */
class ReprocessingTest {
    private val world = World(seed = 2026)
    private val migration = Migration(world.log, world.v1)

    private fun caughtUpV2(): Job {
        val v2 = migration.startV2(DailyNet(), batch = 400)
        Truth.catchUp(world, migration)
        return v2
    }

    @Test
    fun `once caught up, v2 equals a batch recomputation by event time`() {
        val v2 = caughtUpV2()
        val truth = Truth.netByEventDay(world.log)
        for (m in MERCHANTS) for (day in 0..world.today) {
            assertThat(v2.view.cents(m, day)).describedAs("$m day $day").isEqualTo(truth[m to day] ?: 0)
        }
    }

    @Test
    fun `replay does not pile thirty days of revenue into today`() {
        val v2 = caughtUpV2()
        val truth = Truth.netByEventDay(world.log)

        val todayAll = MERCHANTS.sumOf { v2.view.cents(it, world.today) }
        val historyAll = MERCHANTS.sumOf { m -> (0 until world.today).sumOf { v2.view.cents(m, it) } }

        assertThat(todayAll).isEqualTo(MERCHANTS.sumOf { truth[it to world.today] ?: 0 })
        assertThat(historyAll).isEqualTo(MERCHANTS.sumOf { m -> (0 until world.today).sumOf { truth[m to it] ?: 0 } })
        assertThat(historyAll).isGreaterThan(todayAll * 10)       // the month is in the past, not today
    }

    @Test
    fun `a payment uploaded late counts on the day it happened in v2 and on the day it arrived in v1`() {
        val v2 = caughtUpV2()
        val late = world.log.read(6_000, 1).single()              // the first live record
        assertThat(late.event.paymentId).isEqualTo("pay-late-1")
        assertThat(dayOf(late.event.eventTime)).isEqualTo(world.today - 1)
        assertThat(dayOf(world.arrivedAt(late.offset))).isEqualTo(world.today)

        val netWithout = Truth.netByEventDay(world.log, except = "pay-late-1")
        assertThat(v2.view.cents("m-07", world.today - 1) - (netWithout["m-07" to world.today - 1] ?: 0)).isEqualTo(12_345)
        assertThat(v2.view.cents("m-07", world.today)).isEqualTo(netWithout["m-07" to world.today] ?: 0)

        val grossWithout = Truth.grossByArrivalDay(world, except = "pay-late-1")
        assertThat(world.v1.view.cents("m-07", world.today) - (grossWithout["m-07" to world.today] ?: 0)).isEqualTo(12_345)
    }
}
