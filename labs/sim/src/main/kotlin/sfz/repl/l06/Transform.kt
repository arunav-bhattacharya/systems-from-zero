package sfz.repl.l06

/**
 * Operational transformation for one kind of edit: insert one character.
 *
 * An edit is sent as "insert [char] at [index]", made at [site]. When two sites insert at the same
 * time, each applies its own edit first and the other's later, so the index in the late edit can
 * point at the wrong place. [transform] fixes the index before the edit is applied.
 */
data class Insert(val index: Int, val char: Char, val site: String)

/** Applies one insert to [text]. Given. */
fun applyInsert(text: String, op: Insert): String = StringBuilder(text).insert(op.index, op.char).toString()

/**
 * [op] and [against] were made at the same time on the same text, and [against] has already been
 * applied here. Return [op] with its index moved so it still lands where its author meant.
 *
 * - [against] inserted before [op]'s index: everything from there moved right by one, so add one.
 * - Both at the same index: the insert from the smaller site name goes first. So add one only when
 *   `against.site < op.site`. Every site must use the same rule, or they end up with different text.
 * - [against] inserted after [op]'s index: nothing moved, return [op] as it is.
 */
fun transform(op: Insert, against: Insert): Insert {
    TODO("shift op right by one when against landed before it (ties: smaller site first)")
}

/**
 * Two sites each made a list of inserts, [a] and [b], starting from the same text. Returns `a'`, the
 * inserts of [a] rewritten to apply after all of [b], and `b'`, the inserts of [b] rewritten to apply
 * after all of [a]. Site A then applies `b'` and site B applies `a'`, and they should agree.
 *
 * This is the grid that an OT server runs. Every insert of [a] is transformed against every insert
 * of [b], and each of [b]'s inserts is moved past each insert of [a] on the way. Given: it calls
 * your [transform].
 */
fun transformBoth(a: List<Insert>, b: List<Insert>): Pair<List<Insert>, List<Insert>> {
    var rest = b
    val aOut = mutableListOf<Insert>()
    for (op in a) {
        var moved = op
        val next = mutableListOf<Insert>()
        for (other in rest) {
            val movedNext = transform(moved, other)
            next += transform(other, moved)
            moved = movedNext
        }
        aOut += moved
        rest = next
    }
    return aOut to rest
}
