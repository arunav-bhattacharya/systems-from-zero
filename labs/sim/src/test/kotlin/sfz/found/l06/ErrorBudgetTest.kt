package sfz.found.l06

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

class ErrorBudgetTest {
    private val slo = 0.999
    private val day = 1_440
    private val s = 3 * day           // incidents start on day 4, so even the 3-day window is full of history

    @Test
    fun `a 99_9 percent SLO over 30 days allows 43_2 minutes of full outage`() {
        assertThat(budgetMinutes(0.999)).isCloseTo(43.2, within(1e-9))
        assertThat(budgetMinutes(0.99)).isCloseTo(432.0, within(1e-9))
        assertThat(budgetMinutes(0.99999) * 60).isCloseTo(25.92, within(1e-6))   // seconds
        assertThat(budgetMinutes(0.999, windowDays = 7)).isCloseTo(10.08, within(1e-9))
    }

    @Test
    fun `burn rates and the budget they spend`() {
        assertThat(burnRate(0.001, slo)).isCloseTo(1.0, within(1e-9))
        assertThat(burnRate(0.02, slo)).isCloseTo(20.0, within(1e-9))
        assertThat(burnRate(1.0, slo)).isCloseTo(1_000.0, within(1e-6))
        assertThat(budgetSpent(14.4, 60.0)).isCloseTo(0.02, within(1e-12))      // the Workbook's fast-burn page
        assertThat(budgetSpent(6.0, 360.0)).isCloseTo(0.05, within(1e-12))
        assertThat(budgetSpent(1.0, 3.0 * day)).isCloseTo(0.10, within(1e-12))
        assertThat(budgetSpent(1_000.0, 43.2)).isCloseTo(1.0, within(1e-12))    // a full outage empties it in 43.2 min
    }

    @Test
    fun `the error ratio covers the window that ends at the given minute`() {
        val series = listOf(Minute(100, 1), Minute(100, 0), Minute(100, 9), Minute(0, 0))
        assertThat(errorRatio(series, end = 2, windowMinutes = 1)).isCloseTo(0.09, within(1e-12))
        assertThat(errorRatio(series, end = 2, windowMinutes = 2)).isCloseTo(0.045, within(1e-12))
        assertThat(errorRatio(series, end = 2, windowMinutes = 60)).isCloseTo(10.0 / 300, within(1e-12))  // only 3 minutes exist
        assertThat(errorRatio(series, end = 3, windowMinutes = 1)).isEqualTo(0.0)                         // no traffic
        assertThat(errorRatio(series, end = 3, windowMinutes = 3)).isCloseTo(9.0 / 200, within(1e-12))
    }

    @Test
    fun `a ten-minute total outage pages within a minute, and every alert clears on its short window`() {
        val alerts = replay(traffic(s + day, Incident(s, 10, 1.0)), slo)
        assertThat(alerts).containsExactly(
            Alert("fast burn", Action.PAGE, s, s + 14),
            Alert("medium burn", Action.PAGE, s + 2, s + 39),
            Alert("slow burn", Action.TICKET, s + 4, s + 369),
        )
        assertThat(budgetSpent(burnRate(1.0, slo), 10.0)).isCloseTo(0.2315, within(1e-4))
    }

    @Test
    fun `a 2 percent elevation pages after 44 minutes, when 2 percent of the budget is gone`() {
        val series = traffic(s + day, Incident(s, 100, 0.02))
        assertThat(replay(series, slo)).containsExactly(Alert("fast burn", Action.PAGE, s + 43, s + 101))
        assertThat(budgetSpent(burnRate(0.02, slo), 44.0)).isCloseTo(0.0204, within(1e-4))
        // without the 5-minute window the page would stay up for 15 more minutes after the fix
        val longOnly = Rule("long only", 60, 60, 14.4, Action.PAGE)
        assertThat(replay(series, slo, listOf(longOnly))).containsExactly(Alert("long only", Action.PAGE, s + 43, s + 116))
    }

    @Test
    fun `a slow leak never pages but opens a ticket when 10 percent of the budget is gone`() {
        val alerts = replay(traffic(s + 3 * day + 400, Incident(s, 3 * day, 0.0035)), slo)
        assertThat(alerts).containsExactly(Alert("slow burn", Action.TICKET, s + 1_234, s + 3 * day + 257))
        assertThat(budgetSpent(burnRate(0.0035, slo), 1_235.0)).isCloseTo(0.10, within(1e-3))
    }

    @Test
    fun `a short blip wakes the naive alert but not the burn-rate rules`() {
        val series = traffic(s + day, Incident(s, 10, 0.006))
        assertThat(replay(series, slo)).isEmpty()
        assertThat(replay(series, slo, listOf(NAIVE_RULE))).containsExactly(Alert("naive 10 min", Action.PAGE, s + 1, s + 18))
        assertThat(budgetSpent(burnRate(0.006, slo), 10.0)).isLessThan(0.0015)   // 0.14% of the month
    }

    @Test
    fun `two outages are two episodes of the same rule`() {
        val series = traffic(s + day, Incident(s, 3, 1.0), Incident(s + 120, 3, 1.0))
        val fast = replay(series, slo).filter { it.rule == "fast burn" }
        assertThat(fast).containsExactly(
            Alert("fast burn", Action.PAGE, s, s + 7),
            Alert("fast burn", Action.PAGE, s + 120, s + 127),
        )
        val still = replay(traffic(s + 30, Incident(s, 30, 1.0)), slo).first()
        assertThat(still).isEqualTo(Alert("fast burn", Action.PAGE, s, null))   // the history ends mid-outage
    }
}
