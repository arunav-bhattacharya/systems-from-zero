package sfz.repl.l06.demo

/**
 * Two agents edit the same dispute note, "pay 40", at the same moment. Agent a types "$" before
 * the 4, agent b types "!" at the end. Each edit travels as "insert this character at this index".
 */
private data class OtIns(val index: Int, val char: Char, val site: String) {
    override fun toString() = "insert '$char' at $index"
}

private fun applyIns(text: String, op: OtIns) = StringBuilder(text).insert(op.index, op.char).toString()

/** Move [op] past [against], which was made at the same time and has already been applied. */
private fun transform(op: OtIns, against: OtIns): OtIns =
    if (against.index < op.index || (against.index == op.index && against.site < op.site)) op.copy(index = op.index + 1) else op

private fun show(base: String, mine: OtIns, theirs: OtIns) {
    val local = applyIns(base, mine)
    println("site ${mine.site}: \"$base\" -> $mine -> \"$local\"")
    println("    receives $theirs")
    println("    replayed as sent:  \"${applyIns(local, theirs)}\"")
    val moved = transform(theirs, mine)
    println("    transformed to $moved: \"${applyIns(local, moved)}\"")
}

fun main() {
    val base = "pay 40"
    val dollar = OtIns(4, '$', "a")
    val bang = OtIns(6, '!', "b")
    show(base, dollar, bang)
    show(base, bang, dollar)

    println()
    println("same index on both sites: the smaller site name goes first, everywhere")
    val x = OtIns(4, 'x', "a")
    val y = OtIns(4, 'y', "b")
    println("site a: \"${applyIns(applyIns(base, x), transform(y, x))}\"   site b: \"${applyIns(applyIns(base, y), transform(x, y))}\"")
}
