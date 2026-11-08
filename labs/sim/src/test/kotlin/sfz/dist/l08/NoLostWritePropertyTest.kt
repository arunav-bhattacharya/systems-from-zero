package sfz.dist.l08

import net.jqwik.api.Arbitraries
import net.jqwik.api.Arbitrary
import net.jqwik.api.Combinators
import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.Provide
import org.assertj.core.api.Assertions.assertThat

/**
 * The same bug, found a second way. jqwik generates the fault itself (a pause, a cut or a crash,
 * with its start and length) instead of drawing it from a seed. When a property fails, jqwik
 * shrinks the fault towards the smallest start and length that still fail and reports that case,
 * which reads as a one-line bug report: "a pause of n1 at 100 ms for 171 ms loses a write".
 */
class NoLostWritePropertyTest {

    @Provide
    fun faults(): Arbitrary<Fault> {
        val at = Arbitraries.longs().between(100, 900)
        val length = Arbitraries.longs().between(10, 300)
        return Arbitraries.oneOf(
            Arbitraries.just(Fault.None),
            Combinators.combine(at, length).`as` { a, l -> Fault.Pause(a, l) },
            Combinators.combine(at, length).`as` { a, l -> Fault.Cut(a, l) },
            at.map { Fault.Crash(it) },
        )
    }

    @Property(tries = 300)
    fun `with your protocol no acknowledged write is ever lost`(
        @ForAll("faults") fault: Fault,
        @ForAll seed: Long,
    ) {
        val run = Simulation(seed, Protocol.FIXED, fault).run()
        assertThat(run.violation).`as`("seed %d, %s", seed, fault).isNull()
    }

    @Property(tries = 300)
    fun `with your protocol no client ever reads a value older than one it saw acknowledged`(
        @ForAll("faults") fault: Fault,
        @ForAll seed: Long,
    ) {
        // the black-box version: only the client's history, as Jepsen would check it, over the whole run
        val run = Simulation(seed, Protocol.FIXED, fault, stopAtViolation = false).run()
        assertThat(staleReads(run.history)).`as`("seed %d, %s", seed, fault).isEmpty()
    }
}
