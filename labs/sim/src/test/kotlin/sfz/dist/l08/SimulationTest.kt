package sfz.dist.l08

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Exercises 1 to 3: the simulator replays, the search finds the naive protocol's bug, and your
 * epochs fix it. Every run is virtual time: thousands of simulated seconds take about a second.
 */
class SimulationTest {

    @Test
    fun `one seed always gives the same run, event for event`() {
        val first = Simulation(7, Protocol.NAIVE).run()
        val again = Simulation(7, Protocol.NAIVE).run()
        assertThat(again.trace).isEqualTo(first.trace)
        assertThat(again).isEqualTo(first)
        assertThat(Simulation(8, Protocol.NAIVE).run().trace).isNotEqualTo(first.trace)
    }

    @Test
    fun `the search finds a seed where the naive protocol loses an acknowledged write`() {
        val failure = Dst.search(0L..999L, Protocol.NAIVE)
        assertThat(failure).isNotNull()
        assertThat(failure!!.violation).contains("was acknowledged")
        // a pause or a cut longer than the failover timeout; a crash alone can't do it
        assertThat(failure.fault).isInstanceOfAny(Fault.Pause::class.java, Fault.Cut::class.java)
    }

    @Test
    fun `the failing seed replays to the same violation at the same moment`() {
        val failure = Dst.search(0L..999L, Protocol.NAIVE)!!
        val replay = Dst.replay(failure)
        assertThat(replay.violation).isEqualTo(failure.violation)
        assertThat(replay.trace).isEqualTo(failure.trace)
    }

    @Test
    fun `crashes alone never break the naive protocol`() {
        // synchronous replication: everything acknowledged is already on the backup when the primary dies
        assertThat(Dst.search(0L..499L, Protocol.NAIVE) { seed -> Fault.Crash(100 + seed) }).isNull()
    }

    @Test
    fun `a deposed primary steps down instead of overwriting the new one`() {
        val run = Simulation(1, Protocol.FIXED, Fault.Pause(at = 300, forMs = 250)).run()
        assertThat(run.violation).isNull()
        assertThat(run.trace).anyMatch { it.contains("n2: heard nothing") }
        assertThat(run.trace).anyMatch { it.contains("n1: ") && it.contains("steps down") }
    }

    @Test
    fun `the fixed protocol survives 2,000 seeds`() {
        val failure = Dst.search(0L..1_999L, Protocol.FIXED)
        assertThat(failure?.violation).`as`("seed ${failure?.seed}, fault ${failure?.fault}").isNull()
    }
}
