package sfz.dist.l01

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.DoubleRange
import net.jqwik.api.constraints.IntRange
import net.jqwik.api.constraints.LongRange
import org.assertj.core.api.Assertions.assertThat

/**
 * Property tests: jqwik picks seeds, loss and duplication rates, queueing and retry counts, and
 * shrinks any failure to the smallest case. They state the lesson's rules for every network.
 */
class PartialFailurePropertyTest {

    @Property(tries = 150)
    fun `with idempotency keys no card is ever charged twice`(
        @ForAll seed: Long,
        @ForAll @DoubleRange(min = 0.0, max = 0.5) loss: Double,
        @ForAll @DoubleRange(min = 0.0, max = 0.5) duplicate: Double,
        @ForAll @DoubleRange(min = 0.0, max = 0.3) queueing: Double,
        @ForAll @IntRange(min = 1, max = 5) attempts: Int,
    ) {
        val faults = Faults(loss = loss, duplicate = duplicate, maxDelayMs = 20, queueing = queueing, queueMs = 2_000)
        val run = payments(seed = seed, faults = faults, count = 100, maxAttempts = attempts, timeoutMs = 300)
        assertThat(run.audit.extraCharges).isZero()
        assertThat(run.audit.payments).isEqualTo(100)
    }

    @Property(tries = 150)
    fun `an approved payment was charged, with the code the client heard`(
        @ForAll seed: Long,
        @ForAll @DoubleRange(min = 0.0, max = 0.5) loss: Double,
        @ForAll @DoubleRange(min = 0.0, max = 0.5) duplicate: Double,
        @ForAll @IntRange(min = 1, max = 5) attempts: Int,
        @ForAll dedupe: Boolean,
    ) {
        val run = payments(seed = seed, faults = Faults(loss = loss, duplicate = duplicate, maxDelayMs = 20),
            count = 100, maxAttempts = attempts, timeoutMs = 300, dedupe = dedupe)
        val codes = run.server.charges.groupBy({ it.key }, { it.code })
        for ((key, outcome) in run.client.outcomes) {
            if (outcome is Outcome.Approved) assertThat(codes[key]).contains(outcome.code)
        }
    }

    @Property(tries = 100)
    fun `while a dead issuer and a paused one are silent, the client can't tell them apart`(
        @ForAll @LongRange(min = 100, max = 2_000) timeoutMs: Long,
        @ForAll @IntRange(min = 1, max = 4) attempts: Int,
    ) {
        // the pause outlasts every attempt, so no reply can come back before the client decides
        val pauseEnd = timeoutMs * attempts + 1_000
        val dead = payments(count = 1, timeoutMs = timeoutMs, maxAttempts = attempts) { it.server.crash() }
        val paused = payments(count = 1, timeoutMs = timeoutMs, maxAttempts = attempts) { it.server.pauseUntil(pauseEnd) }
        assertThat(dead.client.outcomes).isEqualTo(paused.client.outcomes)
        assertThat(dead.server.charges).isEmpty()
        assertThat(paused.server.charges).hasSize(1)
    }
}
