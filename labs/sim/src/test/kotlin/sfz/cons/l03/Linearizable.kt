package sfz.cons.l03

/** One operation on the register, as a client saw it (test helper). */
data class Op(
    val start: Long,
    val end: Long,
    val cas: Boolean,
    val value: String?,
    val expected: String? = null,
    val ok: Boolean = true,
)

/**
 * A small Wing and Gong style checker for a register with read and compare-and-set (test helper, the
 * same search as lesson cons-02's lab): place a minimal operation whose answer fits the state, go
 * deeper, take it back on a dead end, and never explore the same (placed set, value) twice.
 */
fun linearizable(ops: List<Op>): Boolean {
    val all = ops.sortedBy { it.start }
    val placed = BooleanArray(all.size)
    val seen = HashSet<Pair<List<Boolean>, String?>>()
    fun go(count: Int, state: String?): Boolean {
        if (count == all.size) return true
        if (!seen.add(placed.toList() to state)) return false
        val minEnd = all.indices.filter { !placed[it] }.minOf { all[it].end }
        for (i in all.indices) {
            if (placed[i] || all[i].start > minEnd) continue
            val op = all[i]
            val next = when {
                !op.cas -> if (op.value == state) state else continue
                state == op.expected -> if (op.ok) op.value else continue
                else -> if (!op.ok) state else continue
            }
            placed[i] = true
            if (go(count + 1, next)) return true
            placed[i] = false
        }
        return false
    }
    return go(0, null)
}
