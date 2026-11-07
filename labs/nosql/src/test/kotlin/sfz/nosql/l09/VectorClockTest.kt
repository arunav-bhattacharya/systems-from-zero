package sfz.nosql.l09

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class VectorClockTest {
    private fun vc(vararg entries: Pair<String, Long>) = VectorClock(mapOf(*entries))

    @Test
    fun `compare tells ancestors, descendants, equals and concurrent clocks apart`() {
        val d2 = vc("Sx" to 2)
        val d3 = vc("Sx" to 2, "Sy" to 1)
        val d4 = vc("Sx" to 2, "Sz" to 1)

        assertThat(d2.compare(d3)).isEqualTo(Order.BEFORE)
        assertThat(d3.compare(d2)).isEqualTo(Order.AFTER)
        assertThat(d3.compare(vc("Sy" to 1, "Sx" to 2))).isEqualTo(Order.EQUAL)
        assertThat(d3.compare(d4)).isEqualTo(Order.CONCURRENT)
        assertThat(d4.compare(d3)).isEqualTo(Order.CONCURRENT)
        // a missing node counts as 0
        assertThat(VectorClock().compare(d2)).isEqualTo(Order.BEFORE)
        assertThat(vc("Sx" to 1, "Sy" to 0).compare(vc("Sx" to 1))).isEqualTo(Order.EQUAL)
    }

    @Test
    fun `merge takes the bigger counter for every node, and has seen both clocks`() {
        val d3 = vc("Sx" to 2, "Sy" to 1)
        val d4 = vc("Sx" to 1, "Sz" to 3)
        val merged = d3.merge(d4)

        assertThat(merged).isEqualTo(vc("Sx" to 2, "Sy" to 1, "Sz" to 3))
        assertThat(d3.compare(merged)).isIn(Order.BEFORE)
        assertThat(d4.compare(merged)).isIn(Order.BEFORE)
        assertThat(d4.merge(d3)).isEqualTo(merged)
    }

    @Test
    fun `Dynamo's D1 to D5 cart example, replica by replica`() {
        val sx = DynamoKey()
        val sy = DynamoKey()
        val sz = DynamoKey()

        // D1 and D2: two writes through Sx, the second one based on the first
        val d1 = sx.put("cart: book", VectorClock(), "Sx")
        assertThat(d1.clock).isEqualTo(vc("Sx" to 1))
        val d2 = sx.put("cart: book, pen", d1.clock, "Sx")
        assertThat(d2.clock).isEqualTo(vc("Sx" to 2))
        assertThat(sx.versions).containsExactly(d2) // D2 descends from D1, so D1 is gone

        // D2 reaches the other two replicas
        sy.receive(sx.versions)
        sz.receive(sx.versions)

        // D3 and D4: two clients both read D2 and write at once, through different replicas
        val d3 = sy.put("cart: book, pen, lamp", d2.clock, "Sy")
        val d4 = sz.put("cart: book, pen, mug", d2.clock, "Sz")
        assertThat(d3.clock).isEqualTo(vc("Sx" to 2, "Sy" to 1))
        assertThat(d4.clock).isEqualTo(vc("Sx" to 2, "Sz" to 1))

        // Sx gets both: neither descends from the other, so it keeps both as siblings
        sx.receive(listOf(d3))
        sx.receive(listOf(d4))
        assertThat(sx.versions).containsExactlyInAnyOrder(d3, d4)

        // D5: a client reads both siblings, merges the carts and writes through Sx with their context
        val context = sx.context()
        assertThat(context).isEqualTo(vc("Sx" to 2, "Sy" to 1, "Sz" to 1))
        val d5 = sx.put("cart: book, pen, lamp, mug", context, "Sx")
        assertThat(d5.clock).isEqualTo(vc("Sx" to 3, "Sy" to 1, "Sz" to 1))
        assertThat(sx.versions).containsExactly(d5)

        // D5 replaces D3 on Sy too, because it descends from it
        sy.receive(listOf(d5))
        assertThat(sy.versions).containsExactly(d5)
    }

    @Test
    fun `an old version arriving late changes nothing`() {
        val key = DynamoKey()
        val first = key.put("balance 10000", VectorClock(), "Sx")
        val second = key.put("balance 7000", first.clock, "Sx")
        key.receive(listOf(first)) // a slow replica sends the old version again
        assertThat(key.versions).containsExactly(second)
    }
}
