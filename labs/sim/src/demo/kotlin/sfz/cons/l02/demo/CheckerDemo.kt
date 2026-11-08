package sfz.cons.l02.demo

import kotlin.random.Random

/**
 * Lesson cons-02: the checker on the lesson's history, then the cost of checking as concurrency grows.
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l02.demo.CheckerDemoKt -q
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l02.demo.CheckerDemoKt -Pargs=cost -q
 */
fun main(args: Array<String>) {
    if (args.firstOrNull() == "cost") cost() else lesson()
}

private fun lesson() {
    // the stepper's history: a capture is written while three services read the payment's status
    val h = history {
        "capture".write("status", 2, 0..60)
        "ledger".read("status", null, 5..15)
        "fraud".read("status", 2, 20..30)
        "email".read("status", null, 40..50)
    }
    report("as recorded", h)
    val fixed = history {
        "capture".write("status", 2, 0..60)
        "ledger".read("status", null, 5..15)
        "fraud".read("status", 2, 20..30)
        "email".read("status", 2, 40..50)
    }
    report("with email's read returning 2", fixed)
}

private fun report(title: String, h: History) {
    val r = check(h)
    println("$title: linearizable ${if (r.linearizable) "yes" else "no"} (${r.explored} search steps)")
    println((if (r.linearizable) "  linearization: " else "  longest prefix: ") + r.order.joinToString(", "))
}

/**
 * Random histories from one atomic register, [clients] clients at once, 6 operations each, with the
 * last read changed to a value that makes the history non-linearizable, so the search must try
 * everything before it can say no.
 */
private fun cost() {
    println("clients  ops   steps with cache   steps without cache")
    for (clients in 2..8) {
        var with = 0L
        var without = 0L
        var gaveUp = false
        val runs = 3
        for (seed in 1L..runs) {
            val ops = badHistory(Random(seed * 1_000 + clients), clients)
            with += checkKey(ops).explored
            val r = checkKey(ops, cache = false, budget = 5_000_000)
            without += r.explored
            if (r.explored > 5_000_000) gaveUp = true
        }
        println("%7d  %3d   %16d   %19s".format(clients, clients * 6, with / runs, if (gaveUp) "> 5,000,000" else "%d".format(without / runs)))
    }
}

private fun badHistory(r: Random, clients: Int): List<Op> {
    val bars = (0 until clients).flatMap { c ->
        var t = r.nextLong(0, 3)
        List(6) { val s = t; val e = s + r.nextLong(20, 40); t = e + 1; Triple("c$c", s, e) }
    }
    val points = bars.map { (_, s, e) -> r.nextLong(s, e + 1) }
    var state: Int? = null
    var next = 1
    val ops = bars.indices.sortedWith(compareBy({ points[it] }, { it })).map { i ->
        val (p, s, e) = bars[i]
        if (r.nextInt(3) == 0) Op(i, p, "x", Kind.WRITE, next++, s, e).also { state = it.value }
        else Op(i, p, "x", Kind.READ, state, s, e)
    }.toMutableList()
    // the last read now returns a value nobody wrote: no order can explain it
    val last = ops.indices.last { ops[it].kind == Kind.READ }
    ops[last] = ops[last].copy(value = 999)
    return ops
}
