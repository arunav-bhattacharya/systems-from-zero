package sfz.repl.l01

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.LongRange
import org.assertj.core.api.Assertions.assertThat

/**
 * Property tests: jqwik picks hundreds of delays, write rates and crash times, and shrinks any
 * failure to the smallest case. Together they state the lesson's rule: an asynchronous failover
 * loses exactly the writes acknowledged in the last one-way delay to the nearest follower, and a
 * failover after waiting for one follower loses nothing.
 */
class FailoverPropertyTest {
    private fun crashAndFailover(mode: Mode, d1: Long, d2: Long, everyMs: Long, crashAt: Long): Pair<Cluster, FailoverResult> {
        val sim = Sim()
        val cluster = Cluster(sim, mode, mapOf("f1" to d1, "f2" to d2))
        cluster.writeEvery(everyMs, from = 0, until = 2_000)
        sim.at(crashAt) { cluster.crash(cluster.leader) }
        sim.runUntil(crashAt)
        return cluster to cluster.failover()
    }

    @Property(tries = 200)
    fun `waiting for one follower never loses an acknowledged write`(
        @ForAll @LongRange(min = 1, max = 200) d1: Long,
        @ForAll @LongRange(min = 1, max = 200) d2: Long,
        @ForAll @LongRange(min = 1, max = 20) everyMs: Long,
        @ForAll @LongRange(min = 1, max = 2_500) crashAt: Long,
    ) {
        val (_, result) = crashAndFailover(Mode.Sync(1), d1, d2, everyMs, crashAt)
        assertThat(result.lost).isEmpty()
    }

    @Property(tries = 200)
    fun `asynchronous failover loses exactly the writes acknowledged within one delay of the crash`(
        @ForAll @LongRange(min = 1, max = 200) d1: Long,
        @ForAll @LongRange(min = 1, max = 200) d2: Long,
        @ForAll @LongRange(min = 1, max = 20) everyMs: Long,
        @ForAll @LongRange(min = 1, max = 2_500) crashAt: Long,
    ) {
        val (cluster, result) = crashAndFailover(Mode.Async, d1, d2, everyMs, crashAt)
        val nearest = minOf(d1, d2)
        // an entry written at t reaches the nearest follower at t + nearest; the crash at the same instant runs first
        val expected = cluster.acknowledged.filter { it.ackedAt + nearest >= crashAt }
        assertThat(result.lost).isEqualTo(expected)
    }
}
