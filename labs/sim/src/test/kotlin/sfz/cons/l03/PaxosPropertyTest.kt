package sfz.cons.l03

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Agreement and validity on a hostile network: lost, duplicated and reordered messages, acceptors
 * that crash and come back, proposers that crash for good. Paxos promises safety in every one of
 * these runs. It promises progress only when timing behaves, so liveness is tested separately.
 */
class PaxosPropertyTest {
    @Property(tries = 500)
    fun `no two proposers ever learn different values, and the value was proposed`(
        @ForAll seed: Long,
        @ForAll @IntRange(min = 0, max = 30) dropPercent: Int,
        @ForAll @IntRange(min = 0, max = 20) duplicatePercent: Int,
        @ForAll @IntRange(min = 2, max = 4) proposers: Int,
        @ForAll @IntRange(min = 0, max = 2) maxDown: Int,
        @ForAll proposersCrash: Boolean,
    ) {
        val values = listOf("capture", "void", "refund", "hold").take(proposers)
        val out = runPaxos(
            PaxosConfig(
                seed = seed, values = values, acceptors = 5,
                dropRate = dropPercent / 100.0, duplicateRate = duplicatePercent / 100.0,
                maxDown = maxDown, proposersCrash = proposersCrash, giveUpAtMs = 5_000,
            ),
        )
        assertThat(out.chosen).describedAs("values a majority accepted").hasSizeLessThanOrEqualTo(1)
        assertThat(out.decisions.values.toSet()).hasSizeLessThanOrEqualTo(1)
        if (out.decisions.isNotEmpty()) assertThat(out.chosen).containsAll(out.decisions.values)
        assertThat(values).containsAll(out.chosen)
    }

    @Test
    fun `with some loss and one crashed acceptor at a time, every run still decides`() {
        for (seed in 1L..200L) {
            val out = runPaxos(PaxosConfig(seed = seed, dropRate = 0.1, maxDown = 1, giveUpAtMs = 10_000))
            assertThat(out.decisions).describedAs("seed $seed").hasSize(2)
        }
    }

    @Test
    fun `without the highest-numbered value rule, proposers can learn different values`() {
        val ownValueAlways: (String, Collection<Promise>) -> String = { own, _ -> own }
        val split = (1L..500L).count { seed ->
            runPaxos(PaxosConfig(seed = seed, dropRate = 0.2, maxDown = 2), ownValueAlways).chosen.size > 1
        }
        assertThat(split).describedAs("runs where two values were chosen").isPositive()
    }
}
