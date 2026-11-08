package sfz.cons.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * The checker (exercise 1) on histories recorded from the simulated stores, 200 seeds each, and the
 * quorum store's read repair (exercise 2). Each seed is one exact run: re-run a failing seed with
 * `record(seed) { ... }` and print the history.
 */
class StoresTest {
    private val seeds = 1L..200L

    private fun violations(store: (Network) -> Store, keys: List<String> = listOf("balance")): List<Long> =
        seeds.filter { !Linearizability.check(record(it, keys = keys, store = store)).linearizable }

    @Test
    fun `a single leader that serves every read is linearizable, compare-and-set included`() {
        assertThat(violations({ SingleLeaderStore(it) }, keys = listOf("balance", "status"))).isEmpty()
    }

    @Test
    fun `the same store reading from its asynchronous follower is not`() {
        assertThat(violations({ SingleLeaderStore(it, followerReads = true) })).isNotEmpty()
    }

    @Test
    fun `quorum reads and writes with w + r greater than n are not linearizable`() {
        val bad = violations({ QuorumStore(it, n = 3, w = 2, r = 2) })
        assertThat(bad).describedAs("seeds whose history the checker rejects").isNotEmpty()
    }

    @Test
    fun `a bad seed replays exactly, and its longest linearizable prefix stops short`() {
        val seed = violations({ QuorumStore(it) }).first()
        val once = record(seed) { QuorumStore(it) }
        val again = record(seed) { QuorumStore(it) }
        assertThat(again.toString()).isEqualTo(once.toString())
        val prefix = Linearizability.check(once).order
        assertThat(prefix.size).isLessThan(once.ops.size)
    }

    @Test
    fun `waiting for read repair on a write quorum makes the quorum store linearizable`() {
        assertThat(violations({ QuorumStore(it, syncReadRepair = true) })).isEmpty()
        assertThat(violations({ QuorumStore(it, n = 5, w = 3, r = 3, syncReadRepair = true) })).isEmpty()
    }

    @Test
    fun `read repair costs a second round trip on every read`() {
        fun readTime(repair: Boolean): Double = seeds.flatMap { seed ->
            record(seed) { QuorumStore(it, syncReadRepair = repair) }.ops.filter { it.kind == Kind.READ }.map { it.end - it.start }
        }.average()
        val plain = readTime(false)
        val repaired = readTime(true)
        assertThat(repaired).isGreaterThan(plain * 1.5)
    }
}
