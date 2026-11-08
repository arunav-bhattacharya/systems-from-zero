package sfz.repl.l08

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.time.Instant
import kotlin.random.Random

class CrdtTest {
    /** Every order in which three copies can be merged into one. */
    private fun <T> allOrders(a: T, b: T, c: T, merge: (T, T) -> T): List<T> =
        listOf(listOf(a, b, c), listOf(a, c, b), listOf(b, a, c), listOf(b, c, a), listOf(c, a, b), listOf(c, b, a))
            .map { it.reduce(merge) }

    private fun ms(t: String) = Instant.parse(t).toEpochMilli()

    @Test
    fun `LWW keeps the write with the later clock reading, even when that clock is wrong`() {
        // real time 10:00:00: server 2, whose clock is 5 s fast, captures the payment
        val capture = LwwRegister("CAPTURED", ms("2026-11-07T10:00:05Z"), "server-2")
        // real time 10:00:02: server 1, whose clock is right, voids it. This is the later decision.
        val void = LwwRegister("VOIDED", ms("2026-11-07T10:00:02Z"), "server-1")

        // both replicas converge, in either order, on the same answer: the void is gone
        assertThat(capture.merge(void).value).isEqualTo("CAPTURED")
        assertThat(void.merge(capture).value).isEqualTo("CAPTURED")

        // on a tie the node name decides, the same way everywhere
        val a = LwwRegister("A", 100, "server-1")
        val b = LwwRegister("B", 100, "server-2")
        assertThat(a.merge(b)).isEqualTo(b.merge(a)).isEqualTo(b)
    }

    @Test
    fun `vector clocks see what LWW can't, that the capture and the void were concurrent`() {
        val read = VectorClock().increment("server-1") // both servers read this version
        val capture = read.increment("server-2")
        val void = read.increment("server-1")
        assertThat(capture.compare(void)).isEqualTo(Order.CONCURRENT)
    }

    @Test
    fun `a G-Counter merges to the same total in any order, and merging twice changes nothing`() {
        // three replicas count authorizations for M-0042 during a partition
        val eu = GCounter().increment("eu", 40)
        val us = GCounter().increment("us", 25).increment("us", 5)
        val ap = GCounter().increment("ap", 12)

        val results = allOrders(eu, us, ap, GCounter::merge)
        assertThat(results.map { it.value }.distinct()).containsExactly(82)
        val all = results.first()
        assertThat(all.merge(all)).isEqualTo(all)
        assertThat(all.merge(eu)).isEqualTo(all)
        // a stale copy of eu's slot can't pull the count back down
        assertThat(all.merge(GCounter().increment("eu", 10)).value).isEqualTo(82)
    }

    @Test
    fun `a PN-Counter goes down as well as up, and still merges in any order`() {
        // open authorization holds on A-1001: placed and released on different replicas
        val eu = PNCounter().increment("eu", 3).decrement("eu", 1)
        val us = PNCounter().increment("us", 2)
        val ap = PNCounter().decrement("ap", 2)
        assertThat(allOrders(eu, us, ap, PNCounter::merge).map { it.value }.distinct()).containsExactly(2)
    }

    @Test
    fun `an OR-Set removes what the remove saw, and a concurrent add wins`() {
        // a merchant's blocked-card list, replicated to two regions
        val start = ORSet().add("card-4417", "eu:1").add("card-9921", "eu:2")
        var eu = start
        var us = start

        // during a partition: eu removes card-4417; us adds it again (a new fraud report) and removes card-9921
        eu = eu.remove("card-4417")
        us = us.add("card-4417", "us:1").remove("card-9921")
        assertThat(eu.elements).containsExactly("card-9921")
        assertThat(us.elements).containsExactly("card-4417")

        val merged = eu.merge(us)
        assertThat(merged).isEqualTo(us.merge(eu))
        // card-4417: eu removed only the tag it had seen, eu:1; us's new add, us:1, survives
        assertThat(merged.elements).containsExactly("card-4417")
        assertThat(merged.merge(merged)).isEqualTo(merged)
    }

    @Test
    fun `random edits on three replicas converge whatever order the merges happen in`() {
        val random = Random(7)
        val names = listOf("eu", "us", "ap")
        repeat(50) { round ->
            val sets = names.associateWith { ORSet() }.toMutableMap()
            val counters = names.associateWith { PNCounter() }.toMutableMap()
            var tag = 0
            repeat(40) {
                val r = names.random(random)
                val card = "card-${random.nextInt(6)}"
                sets[r] = if (random.nextBoolean()) sets.getValue(r).add(card, "$r:${tag++}") else sets.getValue(r).remove(card)
                counters[r] = if (random.nextBoolean()) counters.getValue(r).increment(r, random.nextLong(1, 10))
                else counters.getValue(r).decrement(r, random.nextLong(1, 10))
                // now and then two replicas sync in one direction
                if (random.nextInt(5) == 0) {
                    val (from, to) = names.shuffled(random)
                    sets[to] = sets.getValue(to).merge(sets.getValue(from))
                    counters[to] = counters.getValue(to).merge(counters.getValue(from))
                }
            }
            val (a, b, c) = names.map { sets.getValue(it) }
            assertThat(allOrders(a, b, c, ORSet::merge).map { it.elements }.distinct()).`as`("round $round").hasSize(1)
            val (x, y, z) = names.map { counters.getValue(it) }
            assertThat(allOrders(x, y, z, PNCounter::merge).map { it.value }.distinct()).`as`("round $round").hasSize(1)
        }
    }
}
