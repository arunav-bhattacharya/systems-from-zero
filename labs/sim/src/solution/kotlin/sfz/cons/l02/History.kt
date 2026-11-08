package sfz.cons.l02

/**
 * Lesson cons-02 (given): histories of a key-value store whose keys are registers with read, write
 * and compare-and-set. Each operation is a bar: the client sent the request at [Op.start] and got the
 * answer at [Op.end] (milliseconds).
 */
enum class Kind { READ, WRITE, CAS }

/**
 * One operation as its client saw it.
 * - READ: [value] is what the read returned (null: the key had never been written).
 * - WRITE: [value] is what it wrote.
 * - CAS: "if the key holds [expected], set it to [value]"; [ok] says whether it did.
 */
data class Op(
    val id: Int,
    val process: String,
    val key: String,
    val kind: Kind,
    val value: Int?,
    val start: Long,
    val end: Long,
    val expected: Int? = null,
    val ok: Boolean = true,
) {
    override fun toString(): String {
        val what = when (kind) {
            Kind.READ -> "r($key)=${value ?: "-"}"
            Kind.WRITE -> "w($key,$value)"
            Kind.CAS -> "cas($key,${expected ?: "-"}->$value)=${if (ok) "ok" else "fail"}"
        }
        return "$process:$what@$start-$end"
    }
}

/** A list of operations; [keys] and [ofKey] split it into one sub-history per key. */
class History(ops: List<Op>) {
    val ops: List<Op> = ops.sortedWith(compareBy({ it.start }, { it.id }))

    init {
        for (op in this.ops) require(op.start <= op.end) { "$op ends before it starts" }
    }

    val keys: List<String> get() = ops.map { it.key }.distinct()
    fun ofKey(key: String): List<Op> = ops.filter { it.key == key }
    override fun toString(): String = ops.joinToString("\n")
}

/** `history { "A".write("x", 1, 0..10); "B".read("x", 1, 5..20); "C".cas("x", 1, 2, true, 30..40) }` */
class HistoryBuilder {
    private val ops = mutableListOf<Op>()
    fun String.write(key: String, value: Int, at: IntRange) {
        ops += Op(ops.size, this, key, Kind.WRITE, value, at.first.toLong(), at.last.toLong())
    }
    fun String.read(key: String, value: Int?, at: IntRange) {
        ops += Op(ops.size, this, key, Kind.READ, value, at.first.toLong(), at.last.toLong())
    }
    fun String.cas(key: String, expected: Int?, value: Int, ok: Boolean, at: IntRange) {
        ops += Op(ops.size, this, key, Kind.CAS, value, at.first.toLong(), at.last.toLong(), expected, ok)
    }
    fun build() = History(ops)
}

fun history(block: HistoryBuilder.() -> Unit): History = HistoryBuilder().apply(block).build()

/**
 * The sequential specification of one register (given): what a single copy, doing one operation at
 * a time, would answer. [step] returns whether [op]'s recorded answer is possible from [state], and
 * the state afterwards. This is Porcupine's `Step(state, input, output) -> (ok, newState)`.
 */
object Register {
    fun step(state: Int?, op: Op): Pair<Boolean, Int?> = when (op.kind) {
        Kind.READ -> (op.value == state) to state
        Kind.WRITE -> true to op.value
        Kind.CAS -> if (state == op.expected) op.ok to (if (op.ok) op.value else state) else !op.ok to state
    }
}
