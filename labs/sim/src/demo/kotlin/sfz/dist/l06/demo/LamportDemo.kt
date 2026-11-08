package sfz.dist.l06.demo

/**
 * Lesson dist-06, section 2: a small history on 3 nodes, with each event's wall clock, Lamport stamp and vector clock,
 * then pairs that Lamport puts in order although neither happened before the other, picking ones where that order
 * is the reverse of what really happened first (the rows are in real-time order).
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l06.demo.LamportDemoKt -q   (-Pargs='5' tries another seed)
 */
fun main(args: Array<String>) {
    val seed = args.firstOrNull()?.toLong() ?: 2L
    val h = Histories.generate(seed, nodes = 3, events = 10, maxSkewMs = 30, delayMs = 2L..15L, meanGapMs = 4)
    val vc = vectorStamps(h)
    val lamport = lamportStamps(h)
    println("clock offsets: " + h.offsets.withIndex().joinToString { (n, o) -> "n$n +$o ms" })
    println(" #  node  event       wall ms  Lamport  vector")
    for ((i, e) in h.events.withIndex()) {
        val what = when (e.kind) { Kind.LOCAL -> "local"; Kind.SEND -> "send m${e.msg}"; Kind.RECEIVE -> "recv m${e.msg}" }
        println("%2d  n%d    %-10s %7d  %-7s  %s".format(i, e.node, what, e.physical, lamport[i], vc[i]))
    }
    val concurrent = h.events.indices.flatMap { a -> h.events.indices.filter { b -> a < b && vc[a] concurrentWith vc[b] }.map { a to it } }
    println("concurrent pairs (vectors incomparable): ${concurrent.size}. Lamport orders every one; some against real time:")
    val reversed = concurrent.filter { (a, b) -> lamport[b] < lamport[a] }     // a really came first (a < b)
    for ((a, b) in reversed.take(3)) {
        println("  #$b ${lamport[b]} sorts before #$a ${lamport[a]}, but #$a happened first; ${vc[a]} and ${vc[b]} are incomparable")
    }
}
