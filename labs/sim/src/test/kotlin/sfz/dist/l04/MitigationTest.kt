package sfz.dist.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class MitigationTest {
    private fun onePause(at: Long, policy: HolderPolicy) =
        simulate(Scenario(durationMs = 6_000, latencyMs = 5L..5L, pauses = mapOf("A" to listOf(Pause(at, 3_000)))), policy)

    @Test
    fun `the careful holder counts its lease from the request, never from the reply`() {
        val careful = Careful(200)
        assertThat(careful.believedExpiry(sentAt = 1_100, handledAt = 4_102, ttlMs = 2_000)).isEqualTo(3_100)
        assertThat(careful.mayStartWork(now = 2_800, believedExpiry = 3_000)).isTrue()
        assertThat(careful.mayStartWork(now = 2_801, believedExpiry = 3_000)).isFalse()
        assertThat(careful.maySendWrite(now = 2_900, believedExpiry = 3_000)).isFalse()
    }

    @Test
    fun `a renewal reply that waited out a pause doesn't extend the careful holder's lease`() {
        // A sends a renewal at 1,100 ms and stops at 1,102 ms; the reply sits in its socket until 4,102 ms
        val naive = staleWrites(onePause(1_102, Naive))
        val careful = staleWrites(onePause(1_102, Careful(0)))
        assertThat(naive.size).`as`("the naive holder believes it has 2 more seconds").isGreaterThanOrEqualTo(10)
        assertThat(careful).isEmpty()
    }

    @Test
    fun `checking again right before sending catches a pause during the work`() {
        assertThat(staleWrites(onePause(1_520, Naive))).hasSize(1)
        assertThat(staleWrites(onePause(1_520, Careful(200)))).isEmpty()
    }

    @Test
    fun `a pause after the last check gets through whatever the margin`() {
        // A passes its final check at 1,560 ms with 1,540 ms left and stops at 1,562 ms, while the write is being sent
        for (margin in listOf(0L, 200L, 500L, 1_000L)) {
            val run = onePause(1_562, Careful(margin))
            assertThat(staleWrites(run)).`as`("margin $margin").hasSize(1)
            assertThat(clobbers(run)).`as`("margin $margin").hasSize(1)
        }
    }

    @Test
    fun `at random, the careful holder cuts the damage more than tenfold but not to zero`() {
        val naive = sweep(Naive, listOf(3_000L), 1..10).getValue(3_000L)
        val careful = sweep(Careful(200), listOf(3_000L), 1..10).getValue(3_000L)
        assertThat(careful).isPositive()
        assertThat(careful * 10).isLessThan(naive)
    }

    @Test
    fun `a longer lease only moves the threshold`() {
        val tenSeconds = Scenario(ttlMs = 10_000, renewBelowMs = 5_000)
        val damage = sweep(Careful(200), listOf(3_000L, 8_000L), 1..5, tenSeconds)
        assertThat(damage.getValue(3_000L)).isZero()        // shorter than what is always left
        assertThat(damage.getValue(8_000L)).isPositive()    // longer than that
    }
}
