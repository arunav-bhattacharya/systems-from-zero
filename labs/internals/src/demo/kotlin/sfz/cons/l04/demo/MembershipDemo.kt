package sfz.cons.l04.demo

/**
 * Checks whether two cluster configurations can elect leaders (or commit entries) without talking to
 * each other: is there a majority of the first and a majority of the second that share no server?
 * The default run replays the 2015 single-server membership bug in Raft: from four servers, one
 * leader adds S5 while a later leader removes S1.
 *
 * Run from labs/: ./gradlew :internals:demo -Pmain=sfz.cons.l04.demo.MembershipDemoKt -q
 * Or pass two configurations: -Pargs='S1,S2,S3 S1,S2,S3,S4'
 */
fun main(args: Array<String>) {
    if (args.size == 2) {
        report(args[0].split(','), args[1].split(','))
        return
    }
    val c = listOf("S1", "S2", "S3", "S4")
    val d = c + "S5"                 // the term-1 leader adds S5
    val e = c - "S1"                 // the term-2 leader removes S1
    println("C = ${show(c)}   D = C + S5 = ${show(d)}   E = C - S1 = ${show(e)}")
    println()
    println("one change at a time:")
    report(c, d)
    report(c, e)
    println()
    println("two changes, each started from C by a different leader:")
    report(d, e)
}

private fun show(servers: Collection<String>) = servers.joinToString(", ", "{", "}")

/** Every set of servers that is a majority of [config]: more than half of its members. */
private fun majorities(config: List<String>): List<Set<String>> {
    val need = config.size / 2 + 1
    return (0 until (1 shl config.size))
        .map { mask -> config.filterIndexed { i, _ -> mask and (1 shl i) != 0 }.toSet() }
        .filter { it.size >= need }
}

private fun report(a: List<String>, b: List<String>) {
    val ma = majorities(a)
    val mb = majorities(b)
    val disjoint = ma.flatMap { x -> mb.filter { y -> x.intersect(y).isEmpty() }.map { y -> x to y } }
    val pairs = ma.size * mb.size
    if (disjoint.isEmpty()) {
        println("  ${show(a)} and ${show(b)}: all $pairs pairs of majorities share a server")
    } else {
        println("  ${show(a)} and ${show(b)}: ${disjoint.size} of $pairs pairs share no server")
        for ((x, y) in disjoint.sortedBy { it.first.size + it.second.size }.take(4)) println("    ${show(x)} and ${show(y)}")
    }
}
