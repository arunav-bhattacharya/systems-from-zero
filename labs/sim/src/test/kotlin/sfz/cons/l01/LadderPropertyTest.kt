package sfz.cons.l01

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import org.assertj.core.api.Assertions.assertThat
import kotlin.random.Random

/**
 * Property tests over random small histories (2 or 3 processes, up to 9 operations, 1 or 2 keys).
 * The first builds histories from a store that really is one copy; the second checks that the
 * models form a ladder: a stronger model always implies the weaker ones.
 */
class LadderPropertyTest {
    /** Random bars for each process, one after another, plus a random value for each read. */
    private fun randomOps(r: Random, readValue: (key: String, written: List<Int>) -> Int?): List<Op> {
        val ops = mutableListOf<Op>()
        val keys = listOf("x", "y").take(1 + r.nextInt(2))
        val written = keys.associateWith { mutableListOf<Int>() }
        var nextValue = 1
        val plan = mutableListOf<Triple<String, Long, Long>>()
        for (p in listOf("A", "B", "C").take(2 + r.nextInt(2))) {
            var t = r.nextLong(0, 20)
            repeat(1 + r.nextInt(3)) {
                val end = t + r.nextLong(0, 30)
                plan += Triple(p, t, end)
                t = end + 1 + r.nextLong(0, 20)
            }
        }
        // writes first so that reads can name any write, even a later one (a "read from the future")
        val kinds = plan.map { if (r.nextBoolean()) Kind.WRITE else Kind.READ }
        val opKeys = plan.map { keys.random(r) }
        for (i in plan.indices) if (kinds[i] == Kind.WRITE) written.getValue(opKeys[i]) += nextValue++
        var w = 0
        val values = written.mapValues { it.value.iterator() }
        for (i in plan.indices) {
            val (p, s, e) = plan[i]
            val key = opKeys[i]
            val value = if (kinds[i] == Kind.WRITE) values.getValue(key).next() else readValue(key, written.getValue(key))
            ops += Op(w++, p, kinds[i], key, value, s, e)
        }
        return ops
    }

    @Property(tries = 300)
    fun `histories from one atomic copy are linearizable, so they satisfy every model`(@ForAll seed: Long) {
        val r = Random(seed)
        val bars = randomOps(r) { _, _ -> null }
        // the store does each op at one instant inside its bar; replay the ops in that order
        val point = bars.associate { it.id to r.nextLong(it.start, it.end + 1) }
        val state = mutableMapOf<String, Int?>()
        val done = bars.sortedWith(compareBy({ point.getValue(it.id) }, { it.id })).map { op ->
            when (op.kind) {
                Kind.WRITE -> op.also { state[op.key] = op.value }
                Kind.READ -> op.copy(value = state[op.key])
            }
        }
        val h = History(done)
        assertThat(classify(h)).describedAs(h.toString()).isEqualTo(Model.entries.toSet())
    }

    @Property(tries = 300)
    fun `a stronger model always implies the weaker ones`(@ForAll seed: Long) {
        val r = Random(seed)
        val h = History(randomOps(r) { _, written -> (listOf<Int?>(null) + written).random(r) })
        val got = classify(h)
        val implies = mapOf(
            Model.LINEARIZABLE to Model.SEQUENTIAL,
            Model.SEQUENTIAL to Model.CAUSAL,
            Model.CAUSAL to Model.READ_YOUR_WRITES,
        )
        for ((strong, weak) in implies) {
            if (strong in got) assertThat(got).describedAs("$strong without $weak in $h").contains(weak)
        }
        if (Model.CAUSAL in got) assertThat(got).describedAs(h.toString()).contains(Model.MONOTONIC_READS)
        assertThat(got).contains(Model.EVENTUAL)
    }
}
