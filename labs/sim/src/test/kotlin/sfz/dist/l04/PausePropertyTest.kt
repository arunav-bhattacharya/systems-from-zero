package sfz.dist.l04

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import net.jqwik.api.constraints.LongRange
import org.assertj.core.api.Assertions.assertThat

class PausePropertyTest {
    /**
     * Between the careful holder's last check and its write landing there are 5 ms of sending and at most 8 ms of
     * network, plus whatever pause hits in between. A margin that covers all three means the write lands in time.
     */
    @Property(tries = 60)
    fun `pauses shorter than the margin, minus send and network time, never cause a stale write`(
        @ForAll @IntRange(min = 1, max = 100_000) seed: Int,
        @ForAll @LongRange(min = 300, max = 900) margin: Long,
        @ForAll @LongRange(min = 1, max = 285) shortBy: Long,
    ) {
        val pause = margin - 13 - shortBy
        val run = simulate(Scenario(seed = seed, durationMs = 120_000, pauseMs = pause, meanPauseGapMs = 1_000), Careful(margin))
        assertThat(staleWrites(run)).`as`("margin $margin, pause $pause").isEmpty()
    }

    @Property(tries = 40)
    fun `any stale write of the careful holder means a pause longer than its margin`(
        @ForAll @IntRange(min = 1, max = 100_000) seed: Int,
        @ForAll @LongRange(min = 20, max = 900) margin: Long,
        @ForAll @LongRange(min = 1_000, max = 4_000) pause: Long,
    ) {
        val run = simulate(Scenario(seed = seed, durationMs = 120_000, pauseMs = pause), Careful(margin))
        for (w in staleWrites(run)) {
            val lateBy = w.landedAt - run.leases.getValue(w.leaseId).expiresAt
            assertThat(lateBy).isLessThan(pause)                       // the pause, not the holder, made it late
            val hit = run.pauses.getValue(w.holder).any { it.startMs < w.sentAt && it.endMs >= w.sentAt - 5 }
            assertThat(hit).`as`("a pause ended just before the write left").isTrue()
        }
    }
}
