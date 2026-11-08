package sfz.batch.l13

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.DoubleRange
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.time.LocalDate

class BackfillTest {
    /** 90 days of history to reprocess: 2026-08-09 to 2026-11-06. */
    private val days = (0 until 90).map { LocalDate.of(2026, 8, 9).plusDays(it.toLong()) }
    private val faults = Faults.random(seed = 7, days = days)
    private val runner = DagRunner(maxRetries = 2, retryDelayMinutes = 5)

    private fun wrongDays(w: Warehouse) = days.count { w.read("daily_totals", it) != listOf(Source.total(it)) }

    @Test
    fun `a load that appends double-counts every day whose load crashed after writing`() {
        val w = Warehouse()
        val runs = runner.backfill(PaymentTasks.dag(PaymentTasks::appendDailyTotal, faults), days, w, maxActiveRuns = 8)
        assertThat(runs.map { it.states["load"] }).describedAs("every load succeeded in the end").containsOnly(TaskState.SUCCESS)
        assertThat(faults.daysHit("load")).isPositive()
        assertThat(wrongDays(w)).describedAs("days with a wrong total").isEqualTo(faults.daysHit("load"))
        for (d in days) {
            val rows = w.read("daily_totals", d)
            assertThat(rows).describedAs("rows for $d").hasSize(runs.first { it.logicalDate == d }.attempts.getValue("load"))
        }
        assertThat(w.total("daily_totals")).isGreaterThan(days.sumOf { Source.total(it) })
    }

    @Test
    fun `a load that overwrites its partition is exact, however the attempts crash`() {
        val w = Warehouse()
        runner.backfill(PaymentTasks.dag(PaymentTasks::overwriteDailyTotal, faults), days, w, maxActiveRuns = 8)
        assertThat(wrongDays(w)).isZero()
        assertThat(w.total("daily_totals")).isEqualTo(days.sumOf { Source.total(it) })
    }

    @Test
    fun `running the same backfill again changes nothing when the load overwrites, and doubles everything when it appends`() {
        val good = Warehouse()
        val bad = Warehouse()
        repeat(2) {
            runner.backfill(PaymentTasks.dag(PaymentTasks::overwriteDailyTotal), days, good, maxActiveRuns = 16)
            runner.backfill(PaymentTasks.dag(PaymentTasks::appendDailyTotal), days, bad, maxActiveRuns = 16)
        }
        val truth = days.sumOf { Source.total(it) }
        assertThat(good.total("daily_totals")).isEqualTo(truth)
        assertThat(bad.total("daily_totals")).isEqualTo(2 * truth)
    }

    @Test
    fun `90 runs of 20 minutes take as many waves as max active runs allows`() {
        fun wallMinutes(active: Int) =
            runner.backfill(PaymentTasks.dag(PaymentTasks::appendDailyTotal), days, Warehouse(), maxActiveRuns = active).maxOf { it.endMinute }
        assertThat(wallMinutes(1)).isEqualTo(90L * 20)
        assertThat(wallMinutes(4)).describedAs("ceil(90 / 4) = 23 waves").isEqualTo(23L * 20)
        assertThat(wallMinutes(16)).describedAs("ceil(90 / 16) = 6 waves").isEqualTo(6L * 20)
    }

    @Test
    fun `run backwards starts with the newest days`() {
        val runs = runner.backfill(PaymentTasks.dag(PaymentTasks::appendDailyTotal), days, Warehouse(), maxActiveRuns = 16, runBackwards = true)
        assertThat(runs.first().logicalDate).isEqualTo(days.last())
        assertThat(runs.filter { it.endMinute <= 20 }.map { it.logicalDate }).containsExactlyElementsOf(days.takeLast(16).reversed())
    }

    @Test
    fun `a load that reads the newest partition copies today's total into every backfilled day`() {
        val w = Warehouse()
        val dag = PaymentTasks.dag(PaymentTasks::latestDailyTotal)
        runner.run(dag, days.last(), w)                        // the scheduled run: today is right
        assertThat(w.read("daily_totals", days.last())).containsExactly(Source.total(days.last()))
        runner.backfill(dag, days.dropLast(1), w, maxActiveRuns = 4)
        val totals = days.map { w.read("daily_totals", it).single() }.toSet()
        assertThat(totals).describedAs("distinct totals across 90 days").containsExactly(Source.total(days.last()))
    }

    @Property(tries = 30)
    fun `for any crash pattern, the overwrite backfill matches the source`(@ForAll seed: Long, @ForAll @DoubleRange(min = 0.0, max = 0.6) rate: Double) {
        val w = Warehouse()
        val f = Faults.random(seed, days, rate)
        runner.backfill(PaymentTasks.dag(PaymentTasks::overwriteDailyTotal, f), days, w, maxActiveRuns = 8)
        assertThat(wrongDays(w)).isZero()
    }
}
