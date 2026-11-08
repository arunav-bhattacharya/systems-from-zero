package sfz.cons.l01

/**
 * Lesson cons-01 (given): a history is what the clients of a store saw. Each operation is a bar on a
 * timeline: the request left at [Op.start] and the answer came back at [Op.end] (milliseconds). The
 * store did the work somewhere inside the bar, and nobody outside the store knows exactly where.
 *
 * Two simplifications keep every check exact and small:
 * - every write to a key writes a value no other write to that key wrote, so each read's value names
 *   the one write it came from ("reads-from"), and
 * - a read that returns `null` saw no write at all: the key's initial state.
 */
enum class Kind { READ, WRITE }

/** One operation by one client process. For a write [value] is what it wrote; for a read, what it returned. */
data class Op(
    val id: Int,
    val process: String,
    val kind: Kind,
    val key: String,
    val value: Int?,
    val start: Long,
    val end: Long,
) {
    override fun toString(): String {
        val what = if (kind == Kind.WRITE) "w" else "r"
        return "$process:$what($key,${value ?: "-"})@$start-$end"
    }
}

/**
 * A checked list of operations. Each process runs one operation at a time (its bars never overlap),
 * which is what makes "program order" well defined.
 */
class History(ops: List<Op>) {
    val ops: List<Op> = ops.sortedWith(compareBy({ it.start }, { it.id }))

    init {
        for (op in this.ops) require(op.start <= op.end) { "$op ends before it starts" }
        for ((_, mine) in this.ops.groupBy { it.process }) {
            mine.zipWithNext().forEach { (a, b) -> require(a.end < b.start) { "$a and $b overlap in one process" } }
        }
        for ((key, writes) in this.ops.filter { it.kind == Kind.WRITE }.groupBy { it.key }) {
            require(writes.all { it.value != null }) { "a write to $key needs a value" }
            require(writes.map { it.value }.toSet().size == writes.size) { "two writes to $key wrote the same value" }
        }
        for (r in this.ops.filter { it.kind == Kind.READ && it.value != null }) {
            require(writeOf(r) != null) { "$r returned a value no write produced" }
        }
    }

    val processes: List<String> get() = ops.map { it.process }.distinct()
    val writes: List<Op> get() = ops.filter { it.kind == Kind.WRITE }

    /** The operations of one process, in the order it ran them. */
    fun of(process: String): List<Op> = ops.filter { it.process == process }

    /** The write a read got its value from, or null if the read saw the initial state. */
    fun writeOf(read: Op): Op? =
        if (read.kind != Kind.READ || read.value == null) null
        else ops.firstOrNull { it.kind == Kind.WRITE && it.key == read.key && it.value == read.value }

    override fun toString(): String = ops.joinToString(", ")
}

/** Builds a history: `history { "A".write("x", 1, 0..10); "B".read("x", null, 20..30) }`. */
class HistoryBuilder {
    private val ops = mutableListOf<Op>()

    fun String.write(key: String, value: Int, at: IntRange) {
        ops += Op(ops.size, this, Kind.WRITE, key, value, at.first.toLong(), at.last.toLong())
    }

    fun String.read(key: String, value: Int?, at: IntRange) {
        ops += Op(ops.size, this, Kind.READ, key, value, at.first.toLong(), at.last.toLong())
    }

    fun build() = History(ops)
}

fun history(block: HistoryBuilder.() -> Unit): History = HistoryBuilder().apply(block).build()

/**
 * The search every model uses (given). Is there one order of [ops] in which
 * - every read returns the latest write to its key that comes before it (or null if none does), and
 * - `a` comes before `b` whenever `mustPrecede(a, b)` is true?
 *
 * It returns such an order, or null if none exists. It places one operation at a time (depth first),
 * only ever placing an operation whose required predecessors are all placed, and it gives up on a
 * branch as soon as a read would return the wrong value. It remembers the dead ends it has seen
 * (which ops are placed, and what each key holds), so each one is explored once.
 */
object Search {
    fun legalOrder(ops: List<Op>, mustPrecede: (Op, Op) -> Boolean): List<Op>? {
        require(ops.size <= 62) { "this search is for small histories" }
        val n = ops.size
        // preds[i]: bit mask of the ops that must come before op i
        val preds = LongArray(n) { i ->
            var mask = 0L
            for (j in 0 until n) if (j != i && mustPrecede(ops[j], ops[i])) mask = mask or (1L shl j)
            mask
        }
        val dead = HashSet<Pair<Long, Map<String, Int?>>>()
        val order = ArrayList<Op>(n)

        fun go(placed: Long, state: Map<String, Int?>): Boolean {
            if (order.size == n) return true
            if (!dead.add(placed to state)) return false
            for (i in 0 until n) {
                if (placed and (1L shl i) != 0L || preds[i] and placed != preds[i]) continue
                val op = ops[i]
                val next = when (op.kind) {
                    Kind.READ -> if (state[op.key] == op.value) state else continue
                    Kind.WRITE -> state + (op.key to op.value)
                }
                order += op
                if (go(placed or (1L shl i), next)) return true
                order.removeAt(order.size - 1)
            }
            return false
        }
        return if (go(0L, emptyMap())) order.toList() else null
    }

    fun exists(ops: List<Op>, mustPrecede: (Op, Op) -> Boolean): Boolean = legalOrder(ops, mustPrecede) != null
}
