package sfz.cons.l02.demo

import java.util.BitSet

/** The reference checker from the lab, with a switch to turn Lowe's cache off so you can see what it saves. */
class Result(val linearizable: Boolean, val order: List<Op>, val explored: Long)

fun checkKey(ops: List<Op>, cache: Boolean = true, budget: Long = Long.MAX_VALUE): Result {
    val all = ops.sortedBy { it.start }
    val n = all.size
    val placed = BitSet(n)
    val seen = HashSet<Pair<BitSet, Int?>>()
    val path = ArrayList<Op>(n)
    var longest: List<Op> = emptyList()
    var explored = 0L

    fun go(state: Int?): Boolean {
        if (path.size == n) return true
        if (explored > budget) return false
        if (cache && !seen.add((placed.clone() as BitSet) to state)) return false
        var minEnd = Long.MAX_VALUE
        for (i in 0 until n) if (!placed[i]) minEnd = minOf(minEnd, all[i].end)
        for (i in 0 until n) {
            if (placed[i]) continue
            val op = all[i]
            if (op.start > minEnd) break
            explored++
            val (possible, next) = Register.step(state, op)
            if (!possible) continue
            placed.set(i); path += op
            if (path.size > longest.size) longest = path.toList()
            if (go(next)) return true
            placed.clear(i); path.removeAt(path.size - 1)
        }
        return false
    }

    val ok = go(null)
    return Result(ok, if (ok) path.toList() else longest, explored)
}

fun check(h: History): Result {
    val order = mutableListOf<Op>()
    var explored = 0L
    for (key in h.keys) {
        val r = checkKey(h.ofKey(key))
        explored += r.explored
        order += r.order
        if (!r.linearizable) return Result(false, r.order, explored)
    }
    return Result(true, order, explored)
}
