package sfz.cons.l05

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.LongRange
import org.junit.jupiter.api.Test
import org.assertj.core.api.Assertions.assertThat
import kotlin.random.Random

/**
 * Property tests: jqwik picks hundreds of seeds, and each seed is a minute of virtual time in which
 * three candidates are paused for up to 8 s (often longer than their 3 s lease) and sometimes crash.
 * Whatever happens, the fenced ledger never goes back to an older leader, and a token always belongs
 * to one candidate. Without the fence, some of the same runs do go back.
 */
class FencingPropertyTest {
    private fun run(seed: Long, fenced: Boolean): Ledger {
        val sim = Sim(seed)
        val coord = Coordinator(sim)
        val ledger = Ledger(sim, fenced)
        val pods = listOf("pod-a", "pod-b", "pod-c").map { Candidate(it, sim, coord, ledger, ttlMs = 3_000, workEveryMs = 250) }
        pods.forEachIndexed { i, p -> sim.at(i * 7L) { p.start() } }
        val chaos = Random(seed)                         // the schedule of trouble, fixed by the seed
        var crashes = 0
        for (t in 1_000L until 60_000L step 1_500L) {
            val p = pods[chaos.nextInt(pods.size)]
            val roll = chaos.nextDouble()
            when {
                roll < 0.35 -> sim.at(t) { p.pause(chaos.nextLong(100, 8_000)) }
                roll < 0.38 && crashes < 2 -> { crashes++; sim.at(t) { p.crash() } }
            }
        }
        sim.runUntil(70_000)
        return ledger
    }

    @Property(tries = 200)
    fun `the fenced ledger's tokens never go down and each token has one writer`(
        @ForAll @LongRange(min = 1, max = 1_000_000) seed: Long,
    ) {
        val ledger = run(seed, fenced = true)
        assertThat(ledger.entries.map { it.token }).isSorted()
        for ((token, writes) in ledger.entries.groupBy { it.token }) {
            assertThat(writes.map { it.writer }.distinct()).`as`("token $token").hasSize(1)
        }
    }

    @Test
    fun `without the fence, some of the same runs let an old leader write after a newer one`() {
        val wentBack = (1L..100L).count { seed ->
            val tokens = run(seed, fenced = false).entries.map { it.token }
            tokens.zipWithNext().any { (a, b) -> b < a }
        }
        assertThat(wentBack).`as`("most runs have a leader paused past its lease").isGreaterThan(50)
    }
}
