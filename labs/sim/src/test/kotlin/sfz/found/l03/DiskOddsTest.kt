package sfz.found.l03

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.data.Offset
import org.assertj.core.data.Percentage
import org.junit.jupiter.api.Test
import kotlin.math.ln
import kotlin.random.Random

class DiskOddsTest {
    private val afr2025 = 0.0136    // Backblaze, whole fleet, 2025

    @Test
    fun `a fleet of 10,000 disks loses about 136 a year`() {
        assertThat(DiskOdds.expectedFailuresPerYear(10_000, afr2025)).isCloseTo(136.0, Offset.offset(1e-9))
    }

    @Test
    fun `a server with 12 disks has about a 15 percent chance of losing one this year`() {
        assertThat(DiskOdds.chanceOfAnyFailure(12, afr2025)).isCloseTo(0.152, Offset.offset(0.001))
        assertThat(DiskOdds.chanceOfAnyFailure(1, afr2025)).isCloseTo(afr2025, Offset.offset(1e-12))
    }

    @Test
    fun `each extra copy makes loss more than 10,000 times rarer, with a one-day repair`() {
        val one = DiskOdds.lossChancePerYear(1, afr2025, 24.0)
        val two = DiskOdds.lossChancePerYear(2, afr2025, 24.0)
        val three = DiskOdds.lossChancePerYear(3, afr2025, 24.0)
        assertThat(one).isCloseTo(0.0137, Offset.offset(0.0001))
        assertThat(two).isCloseTo(1.03e-6, Percentage.withPercentage(2.0))
        assertThat(three).isCloseTo(5.78e-11, Percentage.withPercentage(2.0))
    }

    @Test
    fun `a slower repair widens the window for the second failure`() {
        val day = DiskOdds.lossChancePerYear(2, afr2025, 24.0)
        val week = DiskOdds.lossChancePerYear(2, afr2025, 168.0)
        assertThat(week / day).isCloseTo(7.0, Offset.offset(1e-9))
    }

    @Test
    fun `5,000 mirrored pairs lose some data about once in 200 years`() {
        assertThat(DiskOdds.fleetLossChancePerYear(5_000, 2, afr2025, 24.0)).isCloseTo(0.0051, Offset.offset(0.0002))
    }

    /** Disks that fail at random and come back [repair] hours later; counts the times all copies were down at once. */
    private fun simulateLosses(copies: Int, lambda: Double, repair: Double, hours: Double, seed: Long): Int {
        val rnd = Random(seed)
        val backAt = DoubleArray(copies)
        var now = 0.0
        var losses = 0
        while (now < hours) {
            val alive = (0 until copies).filter { backAt[it] <= now }
            val nextRepair = backAt.filter { it > now }.minOrNull() ?: Double.MAX_VALUE
            if (alive.isEmpty()) { now = nextRepair; continue }
            val nextFail = now - ln(1 - rnd.nextDouble()) / (lambda * alive.size)
            if (nextRepair < nextFail) { now = nextRepair; continue }
            now = nextFail
            backAt[alive[rnd.nextInt(alive.size)]] = now + repair
            if (backAt.all { it > now }) { losses++; backAt.fill(0.0) }
        }
        return losses
    }

    @Test
    fun `the formula agrees with a simulation of failing and repairing disks`() {
        // rates far above real ones, so that tens of millions of simulated hours show hundreds of losses
        val afrFor = { lambdaPerHour: Double -> 1 - kotlin.math.exp(-lambdaPerHour * DiskOdds.HOURS_PER_YEAR) }
        for ((copies, lambda, hours) in listOf(Triple(2, 1e-3, 2e7), Triple(3, 2e-3, 1e8))) {
            val years = hours / DiskOdds.HOURS_PER_YEAR
            val predicted = DiskOdds.lossChancePerYear(copies, afrFor(lambda), 10.0) * years
            val seen = simulateLosses(copies, lambda, 10.0, hours, seed = 11)
            assertThat(seen.toDouble()).`as`("$copies copies").isCloseTo(predicted, Percentage.withPercentage(20.0))
        }
    }
}
