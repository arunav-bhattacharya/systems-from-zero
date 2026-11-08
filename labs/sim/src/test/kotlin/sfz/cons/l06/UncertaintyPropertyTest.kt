package sfz.cons.l06

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.LongRange
import org.assertj.core.api.Assertions.assertThat

/**
 * Property tests: jqwik picks seeds (the traffic pattern) and clock bounds from 0 to 60 ms. Waiting
 * out the uncertainty and restarting above it both give fresh, atomic audits for every one of them;
 * trusting the clocks still gives atomic audits (the intents see to that), just not fresh ones.
 */
class UncertaintyPropertyTest {
    @Property(tries = 60)
    fun `commit wait and restarts never give a stale or fractured audit`(
        @ForAll @LongRange(min = 1, max = 1_000_000) seed: Long,
        @ForAll @LongRange(min = 0, max = 60) epsilon: Long,
    ) {
        for (policy in listOf(Policy.COMMIT_WAIT, Policy.RESTART)) {
            val s = Cluster(policy, epsilon, seed).run(3_000)
            assertThat(s.staleReads).`as`("$policy, epsilon $epsilon").isZero()
            assertThat(s.fracturedReads).`as`("$policy, epsilon $epsilon").isZero()
        }
    }

    @Property(tries = 60)
    fun `trusting the clocks never fractures an audit`(
        @ForAll @LongRange(min = 1, max = 1_000_000) seed: Long,
        @ForAll @LongRange(min = 0, max = 60) epsilon: Long,
    ) {
        assertThat(Cluster(Policy.TRUST_CLOCK, epsilon, seed).run(3_000).fracturedReads).isZero()
    }
}
