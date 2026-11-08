package sfz.cons.l02

import java.util.BitSet

class Result(val linearizable: Boolean, val order: List<Op>, val explored: Long)

/** Lesson cons-02: a Wing and Gong style linearizability checker with Lowe's cache (reference answer). */
object Linearizability {
    fun checkKey(ops: List<Op>): Result {
        val all = ops.sortedBy { it.start }
        val n = all.size
        val placed = BitSet(n)
        val seen = HashSet<Pair<BitSet, Int?>>()     // (which ops are placed, register value): explored already
        val path = ArrayList<Op>(n)
        var longest: List<Op> = emptyList()
        var explored = 0L

        fun go(state: Int?): Boolean {
            if (path.size == n) return true
            if (!seen.add((placed.clone() as BitSet) to state)) return false   // been here by another route
            // an op is minimal if it starts no later than the earliest end among unplaced ops
            var minEnd = Long.MAX_VALUE
            for (i in 0 until n) if (!placed[i]) minEnd = minOf(minEnd, all[i].end)
            for (i in 0 until n) {
                if (placed[i]) continue
                val op = all[i]
                if (op.start > minEnd) break                       // sorted by start: nothing later is minimal
                explored++
                val (possible, next) = Register.step(state, op)
                if (!possible) continue                            // its answer can't happen here
                placed.set(i); path += op
                if (path.size > longest.size) longest = path.toList()
                if (go(next)) return true
                placed.clear(i); path.removeAt(path.size - 1)      // dead end: take it back
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
}
