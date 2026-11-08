package sfz.cons.l02

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import org.assertj.core.api.Assertions.assertThat
import kotlin.random.Random

/**
 * Exercise 1 against brute force: for random histories of up to 6 operations on one key, the checker
 * must agree with trying every order. The brute force is the definition; the checker is the fast way.
 */
class OraclePropertyTest {
    private fun permutations(ops: List<Op>): Sequence<List<Op>> =
        if (ops.isEmpty()) sequenceOf(emptyList())
        else ops.asSequence().flatMap { op -> permutations(ops - op).map { listOf(op) + it } }

    private fun bruteForce(ops: List<Op>): Boolean = permutations(ops).any { order ->
        val realTime = order.indices.all { i -> (i + 1 until order.size).none { j -> order[j].end < order[i].start } }
        var state: Int? = null
        realTime && order.all { op -> Register.step(state, op).let { (ok, next) -> state = next; ok } }
    }

    private fun randomHistory(r: Random): List<Op> {
        val n = 1 + r.nextInt(6)
        val written = (1..n).toList()
        fun pick() = (listOf<Int?>(null) + written).random(r)
        return List(n) { i ->
            val start = r.nextLong(0, 40)
            val end = start + r.nextLong(0, 25)
            when (r.nextInt(3)) {
                0 -> Op(i, "p$i", "x", Kind.WRITE, written[i], start, end)
                1 -> Op(i, "p$i", "x", Kind.READ, pick(), start, end)
                else -> Op(i, "p$i", "x", Kind.CAS, written[i], start, end, expected = pick(), ok = r.nextBoolean())
            }
        }
    }

    @Property(tries = 1_000)
    fun `the checker agrees with trying every order`(@ForAll seed: Long) {
        val ops = randomHistory(Random(seed))
        val expected = bruteForce(ops)
        val r = Linearizability.checkKey(ops)
        assertThat(r.linearizable).describedAs(ops.joinToString("\n")).isEqualTo(expected)
        if (r.linearizable) assertThat(r.order).containsExactlyInAnyOrderElementsOf(ops)
    }

    @Property(tries = 300)
    fun `histories from one atomic register are always linearizable`(@ForAll seed: Long) {
        val r = Random(seed)
        // 4 clients, 6 ops each, with heavy overlap; each op takes effect at one instant in its bar
        val bars = (0 until 4).flatMap { c ->
            var t = r.nextLong(0, 5)
            List(6) {
                val s = t
                val e = s + r.nextLong(1, 30)
                t = e + 1
                Triple("c$c", s, e)
            }
        }
        val points = bars.map { (_, s, e) -> r.nextLong(s, e + 1) }
        var state: Int? = null
        var nextValue = 1
        val ops = bars.indices.sortedWith(compareBy({ points[it] }, { it })).map { i ->
            val (p, s, e) = bars[i]
            when (r.nextInt(3)) {
                0 -> Op(i, p, "x", Kind.WRITE, nextValue++, s, e).also { state = it.value }
                1 -> Op(i, p, "x", Kind.READ, state, s, e)
                else -> {
                    val expected = if (r.nextBoolean()) state else nextValue + 100
                    val v = nextValue++
                    val ok = state == expected
                    if (ok) state = v
                    Op(i, p, "x", Kind.CAS, v, s, e, expected, ok)
                }
            }
        }
        val result = Linearizability.check(History(ops))
        assertThat(result.linearizable).isTrue()
        assertThat(result.order).hasSize(ops.size)
    }
}
