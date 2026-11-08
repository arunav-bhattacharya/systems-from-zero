package sfz.dist.l02

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.LongRange
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * The detectors on simulated links: a heartbeat every second for 300 s, then the node dies.
 * [CALM] takes 1 to 5 ms per heartbeat, [JITTERY] 30 to 830 ms.
 */
class ScenarioTest {
    private val pause = listOf(199_001L until 203_001L)          // the node sends nothing for 4 s

    @Test
    fun `a timeout set for the calm link raises false alarms on the jittery one`() {
        assertThat(score(FixedTimeoutDetector(1_500), Scenario(CALM)).falseAlarms).isZero()
        assertThat(score(FixedTimeoutDetector(1_500), Scenario(JITTERY)).falseAlarms).isGreaterThan(10)
    }

    @Test
    fun `a timeout long enough for the jittery link is slow on both`() {
        val calm = score(FixedTimeoutDetector(3_000), Scenario(CALM))
        val jittery = score(FixedTimeoutDetector(3_000), Scenario(JITTERY))
        assertThat(calm.falseAlarms).isZero()
        assertThat(jittery.falseAlarms).isZero()
        assertThat(calm.detectionMs).isBetween(3_000L, 3_020L)
        assertThat(jittery.detectionMs).isGreaterThan(3_000L)
    }

    @Test
    fun `phi gives each link its own timeout`() {
        val calm = score(PhiAccrualDetector(threshold = 8.0), Scenario(CALM))
        val jittery = score(PhiAccrualDetector(threshold = 8.0), Scenario(JITTERY))
        assertThat(calm.falseAlarms).isZero()
        assertThat(jittery.falseAlarms).isZero()
        assertThat(calm.detectionMs).isBetween(1_500L, 1_700L)  // quick where gaps are regular
        assertThat(jittery.detectionMs).isBetween(2_500L, 4_000L)  // patient where they aren't
    }

    @Test
    fun `a 4-second pause is a false alarm for every detector quicker than 4 seconds`() {
        assertThat(score(PhiAccrualDetector(threshold = 8.0), Scenario(CALM, pauses = pause)).falseAlarms).isEqualTo(1)
        assertThat(score(PhiAccrualDetector(threshold = 12.0), Scenario(CALM, pauses = pause)).falseAlarms).isEqualTo(1)
        assertThat(score(FixedTimeoutDetector(3_000), Scenario(CALM, pauses = pause)).falseAlarms).isEqualTo(1)
        assertThat(score(FixedTimeoutDetector(6_000), Scenario(CALM, pauses = pause)).falseAlarms).isZero()
    }

    @Test
    fun `one long gap in the window makes phi slower to notice the next crash`() {
        val plain = score(PhiAccrualDetector(threshold = 8.0), Scenario(CALM)).detectionMs!!
        val afterPause = score(PhiAccrualDetector(threshold = 8.0), Scenario(CALM, pauses = pause)).detectionMs!!
        assertThat(afterPause).isGreaterThan(plain + 300)
    }

    @Property(tries = 40)
    fun `while a pause lasts, a quick timeout can't tell it from a crash`(
        @ForAll @LongRange(min = 1_100, max = 3_950) timeoutMs: Long,
        @ForAll @LongRange(min = 1, max = 1_000) seed: Long,
    ) {
        val s = score(FixedTimeoutDetector(timeoutMs), Scenario(CALM, pauses = pause, endMs = 300_000, crashAtMs = null, seed = seed))
        assertThat(s.falseAlarms).isEqualTo(1)
    }

    @Property(tries = 40)
    fun `a timeout longer than the pause never suspects the paused node`(
        @ForAll @LongRange(min = 4_050, max = 30_000) timeoutMs: Long,
        @ForAll @LongRange(min = 1, max = 1_000) seed: Long,
    ) {
        val s = score(FixedTimeoutDetector(timeoutMs), Scenario(CALM, pauses = pause, endMs = 300_000, crashAtMs = null, seed = seed))
        assertThat(s.falseAlarms).isZero()
    }
}
