package sfz.dist.l03

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.LongRange
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Exercises 2 and 3: a causal chain of writes from two service instances, pod-a and pod-b, to one
 * last-write-wins register 1 ms away. Each write reads the register first, so it follows the one
 * before it. One round takes about 6 ms: read, write, read back.
 */
class LastWriteWinsTest {
    private fun chain(
        offsetB: Long, boundB: Long = kotlin.math.abs(offsetB), commitWait: Boolean = false,
        rounds: Int = 100, maxThinkMs: Long = 0, seed: Long = 1,
    ): Pair<ChainResult, Store> {
        val sim = Sim(seed)
        val store = Store(sim)
        val a = Writer("pod-a", DriftingClock(sim), sim, store)
        val b = Writer("pod-b", DriftingClock(sim, offsetMs = offsetB, boundMs = boundB), sim, store)
        return causalChain(sim, store, listOf(a, b), rounds, commitWait, maxThinkMs) to store
    }

    @Test
    fun `the higher timestamp wins and a tie goes to the larger writer name`() {
        val r = LwwRegister()
        assertThat(r.apply(Write("captured", 120, "pod-a"))).isTrue()
        assertThat(r.apply(Write("refunded", 108, "pod-b"))).isFalse()      // older stamp: dropped
        assertThat(r.current?.value).isEqualTo("captured")
        assertThat(r.apply(Write("refunded", 120, "pod-b"))).isTrue()       // same stamp: "pod-b" > "pod-a"
        assertThat(r.apply(Write("captured", 120, "pod-a"))).isFalse()
        assertThat(r.current?.value).isEqualTo("refunded")
    }

    @Test
    fun `clocks in step lose nothing`() {
        val (result, _) = chain(offsetB = 0)
        assertThat(result.acknowledged).isEqualTo(100)
        assertThat(result.lost).isEmpty()
    }

    @Test
    fun `a writer whose clock is 20 ms behind loses every write that follows the other's`() {
        val (result, store) = chain(offsetB = -20)
        assertThat(result.acknowledged).isEqualTo(100)             // every write got an OK
        assertThat(result.lost).hasSize(50)                         // and every pod-b write is gone
        assertThat(result.lost).allSatisfy { assertThat(it.removePrefix("v").toInt() % 2).isEqualTo(1) }
        assertThat(store.dropped).isEqualTo(50)
    }

    @Test
    fun `skew smaller than the gap between causal writes does no harm, and a little more loses half`() {
        assertThat(chain(offsetB = -5).first.lost).isEmpty()       // pod-b writes 6 ms after pod-a's write
        assertThat(chain(offsetB = -6).first.lost).isEmpty()       // equal stamps: "pod-b" wins the tie
        assertThat(chain(offsetB = -7).first.lost).hasSize(50)
    }

    @Test
    fun `commit wait keeps every causally later write`() {
        val (result, store) = chain(offsetB = -20, commitWait = true)
        assertThat(result.lost).isEmpty()
        assertThat(store.dropped).isZero()
        // pod-b's bound is 20 ms (plus 1 ms of assumed drift), so it waits out about twice that;
        // pod-a's bound is just the 1 ms of assumed drift, so it waits 1 ms after the OK
        val bWaits = result.waitsMs.filterIndexed { i, _ -> i % 2 == 1 }
        assertThat(bWaits).allSatisfy { assertThat(it).isBetween(37L, 42L) }
        assertThat(result.waitsMs.filterIndexed { i, _ -> i % 2 == 0 }).containsOnly(1L)
    }

    @Test
    fun `commit wait is only as good as the bound`() {
        // pod-b is 20 ms behind but believes it is within 5 ms
        val (result, _) = chain(offsetB = -20, boundB = 5, commitWait = true)
        assertThat(result.lost).isNotEmpty()
    }

    @Property(tries = 200)
    fun `commit wait never loses a causally later write while every bound is honest`(
        @ForAll @LongRange(min = -100, max = 100) offsetB: Long,
        @ForAll @LongRange(min = 0, max = 5) slackMs: Long,
        @ForAll @LongRange(min = 0, max = 20) maxThinkMs: Long,
        @ForAll @LongRange(min = 1, max = 1_000) seed: Long,
    ) {
        val (result, _) = chain(offsetB, boundB = kotlin.math.abs(offsetB) + slackMs, commitWait = true,
            rounds = 30, maxThinkMs = maxThinkMs, seed = seed)
        assertThat(result.lost).isEmpty()
    }

    @Property(tries = 100)
    fun `plain last write wins loses writes whenever the slow clock is behind by more than the gap`(
        @ForAll @LongRange(min = 7, max = 1_000) behindMs: Long,
        @ForAll @LongRange(min = 1, max = 1_000) seed: Long,
    ) {
        val (result, _) = chain(offsetB = -behindMs, rounds = 30, seed = seed)
        assertThat(result.lost).hasSize(15)
    }
}
