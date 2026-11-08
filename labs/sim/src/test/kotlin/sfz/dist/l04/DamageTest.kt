package sfz.dist.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class DamageTest {
    private fun result(writes: List<Write>, vararg leases: Lease) =
        RunResult(writes, leases.associateBy { it.id }, emptyMap(), emptyList())

    private val lease1 = Lease(1, "A", grantedAt = 0, expiresAt = 2_000)
    private val lease2 = Lease(2, "B", grantedAt = 2_050, expiresAt = 4_050)

    @Test
    fun `a write that lands inside its lease is not stale`() {
        val run = result(listOf(Write("A", 1, sentAt = 1_900, landedAt = 1_999)), lease1)
        assertThat(staleWrites(run)).isEmpty()
    }

    @Test
    fun `a write that lands at or after its lease's expiry is stale, whenever it was sent`() {
        val atExpiry = Write("A", 1, sentAt = 1_990, landedAt = 2_000)
        val late = Write("A", 1, sentAt = 500, landedAt = 3_000)
        val run = result(listOf(atExpiry, late), lease1)
        assertThat(staleWrites(run)).containsExactly(atExpiry, late)
    }

    @Test
    fun `a stale write that lands after a newer lease's write is a clobber`() {
        val beforeB = Write("A", 1, sentAt = 1_990, landedAt = 2_010)   // stale, but nothing newer to overwrite yet
        val b = Write("B", 2, sentAt = 2_100, landedAt = 2_105)
        val afterB = Write("A", 1, sentAt = 1_995, landedAt = 2_200)    // overwrites B's update
        val run = result(listOf(beforeB, b, afterB), lease1, lease2)
        assertThat(staleWrites(run)).containsExactly(beforeB, afterB)
        assertThat(clobbers(run)).containsExactly(afterB)
    }

    @Test
    fun `with no pauses the naive holder never writes outside its lease`() {
        for (seed in 1..5) {
            val run = simulate(Scenario(seed = seed), Naive)
            assertThat(run.writes.size).`as`("seed $seed writes").isGreaterThan(5_000)
            assertThat(staleWrites(run)).`as`("seed $seed").isEmpty()
        }
    }

    @Test
    fun `one pause during the work makes the naive holder write after its lease ran out`() {
        // A checks at 1,500 ms with about 1.6 s left, starts 60 ms of work, and stops at 1,520 ms for 3 s
        val run = simulate(Scenario(durationMs = 6_000, latencyMs = 5L..5L, pauses = mapOf("A" to listOf(Pause(1_520, 3_000)))), Naive)
        val stale = staleWrites(run)
        assertThat(stale).hasSize(1)
        assertThat(stale.single().holder).isEqualTo("A")
        assertThat(stale.single().landedAt).isEqualTo(4_530)
        assertThat(clobbers(run)).isEqualTo(stale)   // B had been writing under lease 2 since 3,320 ms
    }

    @Test
    fun `three-second pauses at random leave stale writes in every run`() {
        for (seed in 1..5) {
            val run = simulate(Scenario(seed = seed, pauseMs = 3_000), Naive)
            assertThat(staleWrites(run)).`as`("seed $seed stale").isNotEmpty()
            assertThat(clobbers(run)).`as`("seed $seed clobbers").isNotEmpty()
        }
    }

    @Test
    fun `the damage starts once pauses outlast what is left of the lease`() {
        // the holder renews below 1 s, so it always has about 1 to 2 s left: shorter pauses can't outlast that
        val damage = sweep(Naive, listOf(250L, 1_500L, 3_000L), 1..10)
        assertThat(damage.keys).containsExactly(250L, 1_500L, 3_000L)
        assertThat(damage.getValue(250L)).isZero()
        assertThat(damage.getValue(1_500L)).isGreaterThan(100)
        assertThat(damage.getValue(3_000L)).isGreaterThan(damage.getValue(1_500L))
    }
}
