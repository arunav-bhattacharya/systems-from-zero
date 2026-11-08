package sfz.cons.l02

/**
 * The answer of a check. If [linearizable], [order] is a linearization: every operation once, in an
 * order that respects real time and that one copy ([Register]) could have produced. If not, [order]
 * is the longest such prefix the search found, which is where to start reading. [explored] counts
 * the search steps, so you can watch the cost grow with concurrency.
 */
class Result(val linearizable: Boolean, val order: List<Op>, val explored: Long)

/**
 * Lesson cons-02: a linearizability checker in the style of Wing and Gong (1993), with Lowe's cache
 * of states already explored.
 *
 * The search builds a linearization one operation at a time. At each step it may take any operation
 * not yet placed that is "minimal": no other unplaced operation finished before it started (so
 * putting it next can't break real-time order). It asks [Register.step] whether that operation's
 * recorded answer is possible from the current state. If yes, it places it and goes deeper; if the
 * branch dead-ends, it takes the operation back and tries the next one. If every branch dead-ends,
 * the history is not linearizable.
 *
 * Two operations that are placed in different orders can lead to the same situation: the same set
 * of placed operations and the same register value. Remember those you have already explored and
 * don't explore them twice; without that the search is exponential even on easy histories.
 */
object Linearizability {
    /** Checks the operations on ONE key. Exercise 1. */
    fun checkKey(ops: List<Op>): Result =
        TODO("exercise 1: depth-first search over minimal operations, with a cache of (placed set, state)")

    /**
     * Checks a whole history (given). Herlihy and Wing proved linearizability is local: a history is
     * linearizable exactly when each key's sub-history is. So check the keys one at a time. Splitting
     * like this is what Porcupine calls P-compositionality, and it is most of why it is fast.
     */
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
