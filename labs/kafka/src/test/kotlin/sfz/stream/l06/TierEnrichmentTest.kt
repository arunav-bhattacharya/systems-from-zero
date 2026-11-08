package sfz.stream.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.random.Random

/**
 * Your enrichment topology in TopologyTestDriver. Customer c-1 is silver from 09:00 and gold from 10:00. An order's
 * tier must be the one in force when the order was placed, whatever order the records arrive in.
 */
class TierEnrichmentTest {

    @Test
    fun `an order that arrives on time gets the tier in force`() {
        val out = runTopology(TierEnrichment.build(), listOf(
            tier("c-1", "silver", "09:00"),
            order("c-1", "o-1 40.00", "09:30"),
            tier("c-1", "gold", "10:00"),
            order("c-1", "o-2 75.00", "10:05"),
        ))
        assertThat(out).containsExactly("c-1" to "o-1 40.00 tier=silver", "c-1" to "o-2 75.00 tier=gold")
    }

    @Test
    fun `an order that arrives after the upgrade still gets the tier from when it was placed`() {
        // o-1 was placed at 09:30 but sat in a lagging partition; it arrives after the 10:00 upgrade
        val out = runTopology(TierEnrichment.build(), listOf(
            tier("c-1", "silver", "09:00"),
            tier("c-1", "gold", "10:00"),
            order("c-1", "o-1 40.00", "09:30"),
        ))
        assertThat(out).describedAs("an unversioned table answers with the latest tier, gold")
            .containsExactly("c-1" to "o-1 40.00 tier=silver")
    }

    @Test
    fun `the result does not depend on when each order arrives`() {
        val tiers = listOf(tier("c-1", "silver", "09:00"), tier("c-1", "gold", "10:00"), tier("c-1", "platinum", "11:00"))
        val orders = listOf(order("c-1", "o-1", "09:30"), order("c-1", "o-2", "10:30"), order("c-1", "o-3", "11:30"))
        val expected = setOf("o-1 tier=silver", "o-2 tier=gold", "o-3 tier=platinum")
        val random = Random(7)
        repeat(12) { run ->
            // tiers arrive in time order; each order arrives some time after the tier that applies to it
            val arrivals = tiers.toMutableList()
            for ((i, o) in orders.withIndex()) {
                val earliest = arrivals.indexOf(tiers[i]) + 1
                arrivals.add(random.nextInt(earliest, arrivals.size + 1), o)
            }
            val out = runTopology(TierEnrichment.build(), arrivals).map { it.second }.toSet()
            assertThat(out).describedAs("run $run, arrival order ${arrivals.map { it.value }}").isEqualTo(expected)
        }
    }

    @Test
    fun `an order older than the store's history gets no tier`() {
        // stream time of the table reaches day 10; with 7 days of history, nobody knows the tier on day 1 any more
        val out = runTopology(TierEnrichment.build(), listOf(
            tier("c-1", "silver", "d0 09:00"),
            tier("c-1", "gold", "d10 09:00"),
            order("c-1", "o-1 40.00", "d1 09:00"),
        ))
        assertThat(out).containsExactly("c-1" to "o-1 40.00 tier=none")
    }

    @Test
    fun `the global table version enriches every order and marks unknown customers`() {
        val out = runTopology(TierEnrichment.buildGlobal(), listOf(
            tier("c-1", "gold", "10:00"),
            order("c-1", "o-1 40.00", "10:05"),
            order("c-2", "o-2 9.99", "10:06"),
        ))
        assertThat(out).containsExactly("c-1" to "o-1 40.00 tier=gold", "c-2" to "o-2 9.99 tier=none")
    }
}
