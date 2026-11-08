package sfz.cons.l01

/**
 * Lesson cons-01: which consistency models does a history satisfy? (reference answer)
 *
 * Every model asks: is there an order of some operations that one copy could have produced, and that
 * respects some "a must come before b" relation? The models differ only in which operations and
 * which relation.
 */
enum class Model { LINEARIZABLE, SEQUENTIAL, CAUSAL, READ_YOUR_WRITES, MONOTONIC_READS, EVENTUAL }

/** Real-time order: [a] had its answer before [b] was sent. */
fun realTime(a: Op, b: Op): Boolean = a.end < b.start

/** Program order: same process, [a] first. A process runs one op at a time, so start times decide. */
fun programOrder(a: Op, b: Op): Boolean = a.process == b.process && a.start < b.start

/** Causal order: program order plus reads-from, closed under transitivity. */
fun causalOrder(h: History): (Op, Op) -> Boolean {
    val ops = h.ops
    val n = ops.size
    val index = ops.withIndex().associate { (i, op) -> op.id to i }
    // reach[i][j]: op i happens before op j
    val reach = Array(n) { BooleanArray(n) }
    for (i in 0 until n) for (j in 0 until n) {
        if (programOrder(ops[i], ops[j])) reach[i][j] = true                 // same process, earlier
    }
    for (read in ops) {
        val w = h.writeOf(read) ?: continue
        reach[index.getValue(w.id)][index.getValue(read.id)] = true          // the write it read from
    }
    // Floyd-Warshall style closure: if i -> k and k -> j then i -> j
    for (k in 0 until n) for (i in 0 until n) if (reach[i][k]) for (j in 0 until n) if (reach[k][j]) reach[i][j] = true
    return { a, b -> reach[index.getValue(a.id)][index.getValue(b.id)] }
}

fun satisfies(h: History, model: Model): Boolean {
    // what one process must be able to explain: every write in the system, plus its own operations
    fun view(p: String) = h.ops.filter { it.kind == Kind.WRITE || it.process == p }
    return when (model) {
        // one order for everybody, and it must agree with the clock on the wall
        Model.LINEARIZABLE -> Search.exists(h.ops, ::realTime)
        // one order for everybody, but it only has to agree with each process's own order
        Model.SEQUENTIAL -> Search.exists(h.ops, ::programOrder)
        // one order per process, which must keep cause before effect
        Model.CAUSAL -> {
            val before = causalOrder(h)
            h.processes.all { p -> Search.exists(view(p), before) }
        }
        // per process: my reads come after my own earlier writes
        Model.READ_YOUR_WRITES -> h.processes.all { p ->
            Search.exists(view(p)) { a, b ->
                a.process == p && b.process == p && a.kind == Kind.WRITE && b.kind == Kind.READ && programOrder(a, b)
            }
        }
        // per process: my reads keep their order, so a later read can't see less than an earlier one
        Model.MONOTONIC_READS -> h.processes.all { p ->
            Search.exists(view(p)) { a, b ->
                a.process == p && b.process == p && a.kind == Kind.READ && b.kind == Kind.READ && programOrder(a, b)
            }
        }
        // a liveness promise: no finite history can break it
        Model.EVENTUAL -> true
    }
}

/** Every model [h] satisfies (given). */
fun classify(h: History): Set<Model> = Model.entries.filter { satisfies(h, it) }.toSet()
