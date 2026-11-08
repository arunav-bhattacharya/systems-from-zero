package sfz.found.l05

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test
import kotlin.math.abs

class ScalingTest {
    @Test
    fun `Amdahl caps the speed-up at one over the serial share`() {
        assertThat(amdahl(1, 0.05)).isCloseTo(1.0, within(1e-12))
        assertThat(amdahl(16, 0.05)).isCloseTo(1.0 / (0.05 + 0.95 / 16), within(1e-12))   // about 9.14
        assertThat(amdahl(1_000_000, 0.05)).isCloseTo(20.0, within(0.01))
        assertThat(amdahl(64, 0.0)).isCloseTo(64.0, within(1e-9))
    }

    @Test
    fun `the USL is Amdahl when beta is zero, and turns down when beta is not`() {
        for (n in listOf(1, 2, 8, 64)) assertThat(usl(n, 0.05, 0.0)).isCloseTo(amdahl(n, 0.05), within(1e-9))
        assertThat(usl(1, 0.3, 0.01)).isCloseTo(1.0, within(1e-12))
        assertThat(usl(10, 0.03, 0.0005)).isCloseTo(10.0 / (1 + 0.03 * 9 + 0.0005 * 90), within(1e-12))
        assertThat(usl(64, 0.03, 0.0005)).isLessThan(usl(44, 0.03, 0.0005))     // more workers, less work done
    }

    @Test
    fun `the USL peaks at the square root of one minus alpha over beta`() {
        assertThat(uslPeak(0.03, 0.0005)).isCloseTo(44.05, within(0.01))
        assertThat(uslPeak(0.05, 0.0)).isEqualTo(Double.POSITIVE_INFINITY)
        val peak = uslPeak(0.03, 0.0005).toInt()
        assertThat(usl(peak, 0.03, 0.0005)).isGreaterThan(usl(peak - 5, 0.03, 0.0005))
        assertThat(usl(peak, 0.03, 0.0005)).isGreaterThan(usl(peak + 6, 0.03, 0.0005))
    }

    @Test
    fun `fitting exact USL data gives back alpha and beta`() {
        val measured = listOf(1, 2, 4, 8, 16, 32, 64).associateWith { 1_000.0 * usl(it, 0.05, 0.0002) }
        val fit = fitUsl(measured)
        assertThat(fit.alpha).isCloseTo(0.05, within(1e-9))
        assertThat(fit.beta).isCloseTo(0.0002, within(1e-12))
        assertThat(fit.single).isEqualTo(1_000.0)
        assertThat(fit.throughput(128)).isCloseTo(1_000.0 * usl(128, 0.05, 0.0002), within(1e-6))
    }

    @Test
    fun `the fit predicts where the settlement batch stops getting faster`() {
        val payments = paymentsOfTheDay()
        val counts = listOf(1, 2, 4, 8, 16, 24, 32, 48, 64, 96, 128)
        val measured = counts.associateWith { payments.size / runOnCluster(payments, it).seconds }
        val fit = fitUsl(measured)
        for ((n, x) in measured) {
            assertThat(abs(fit.throughput(n) / x - 1)).describedAs("fit at $n workers").isLessThan(0.08)
        }
        val best = measured.maxBy { it.value }.key                          // 48 in this model
        assertThat(uslPeak(fit.alpha, fit.beta)).isBetween(best * 0.8, best * 1.2)
        assertThat(fit.beta).isGreaterThan(0.0)
    }

    @Test
    fun `COST is the smallest configuration that beats one thread`() {
        assertThat(cost(10.0, { 100.0 / it }, 64)).isEqualTo(11)                 // 100/10 is not < 10
        assertThat(cost(10.0, { 5.0 }, 64)).isEqualTo(1)
        assertThat(cost(10.0, { 2.0 + 100.0 / it + 0.5 * it }, 64)).isNull()      // never below 16.1
    }

    @Test
    fun `the simulated cluster needs 16 workers to beat a plain loop, and never does with a slow shuffle`() {
        val payments = paymentsOfTheDay()
        val one = runOnOneThread(payments)
        assertThat(runOnCluster(payments, 7).totals).isEqualTo(one.totals)     // same answer, slower
        assertThat(cost(one.seconds, { runOnCluster(payments, it).seconds }, 64)).isEqualTo(16)
        val slowShuffle = Costs(perPeerMs = 2.0)
        assertThat(cost(one.seconds, { runOnCluster(payments, it, slowShuffle).seconds }, 64)).isNull()
    }
}
