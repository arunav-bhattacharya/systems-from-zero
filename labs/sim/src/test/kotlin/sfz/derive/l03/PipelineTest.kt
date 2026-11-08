package sfz.derive.l03

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * 1,000 transfers through the whole path, the same faults in every variant (seed 2026). Each
 * layer removes the duplicates it can see; only the request id at the ledger removes them all.
 */
class PipelineTest {
    @Test
    fun `duplicates fall at each layer and reach zero only end to end`() {
        val counts = Variant.entries.associateWith { Pipeline.run(it, seed = 2026).duplicates }

        assertThat(counts[Variant.NONE]).isEqualTo(103)
        assertThat(counts[Variant.TRANSPORT]).isEqualTo(78)            // repeated packets gone
        assertThat(counts[Variant.BROKER]).isEqualTo(47)               // resent batches gone too
        assertThat(counts[Variant.END_TO_END]).isEqualTo(0)
    }

    @Test
    fun `end to end, the money moved is exactly the money asked for`() {
        val none = Pipeline.run(Variant.NONE, seed = 2026)
        val e2e = Pipeline.run(Variant.END_TO_END, seed = 2026)

        assertThat(none.extraCents).isPositive()                  // somebody paid twice
        assertThat(e2e.movedCents).isEqualTo(e2e.askedCents)
        assertThat(e2e.rows).isEqualTo(1_000)
    }

    @Test
    fun `a broker that is exactly-once inside still leaves duplicates in the ledger`() {
        val onlyCrashes = Rates(duplicatePacket = 0.0, lostResponse = 0.0, lostAck = 0.0, consumerCrash = 0.05)
        val broker = Pipeline.run(Variant.BROKER, seed = 2026, rates = onlyCrashes)
        val e2e = Pipeline.run(Variant.END_TO_END, seed = 2026, rates = onlyCrashes)

        assertThat(broker.duplicates).isEqualTo(57)               // one per crash between write and commit
        assertThat(e2e.duplicates).isZero()
    }

    @Property(tries = 40)
    fun `for any seed, end to end leaves no duplicate rows and moves exactly what was asked`(@ForAll seed: Long) {
        val r = Pipeline.run(Variant.END_TO_END, seed, transfers = 300)
        assertThat(r.duplicates).isZero()
        assertThat(r.movedCents).isEqualTo(r.askedCents)

        val none = Pipeline.run(Variant.NONE, seed, transfers = 300).duplicates
        val transport = Pipeline.run(Variant.TRANSPORT, seed, transfers = 300).duplicates
        val broker = Pipeline.run(Variant.BROKER, seed, transfers = 300).duplicates
        assertThat(none).isGreaterThanOrEqualTo(transport)
        assertThat(transport).isGreaterThanOrEqualTo(broker)
    }
}
