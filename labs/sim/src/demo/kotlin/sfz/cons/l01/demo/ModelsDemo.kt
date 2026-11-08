package sfz.cons.l01.demo

/**
 * Lesson cons-01: one history per rung of the ladder, and the models each one satisfies.
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l01.demo.ModelsDemoKt -q              the ladder
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l01.demo.ModelsDemoKt -Pargs=mine -q  your history, from mine() below
 *
 * Keys are payment fields: `status` 1 = authorized, 2 = captured, 3 = refunded; `balance` 70 = 70.00.
 * A read of `-` saw nothing: the key's initial state. Times are milliseconds.
 */
fun main(args: Array<String>) {
    if (args.firstOrNull() == "mine") {
        show("mine", mine())
        return
    }
    show("one copy: every read sees the latest finished write", history {
        "checkout".write("balance", 70, 0..10)
        "ledger".read("balance", 70, 20..30)
    })
    show("stale: ledger starts after the write finished, and misses it", history {
        "checkout".write("balance", 70, 0..10)
        "ledger".read("balance", null, 20..30)
    })
    show("opposite orders: two readers see two concurrent writes differently", history {
        "eu".write("status", 2, 0..10)
        "us".write("status", 3, 0..10)
        "ledger".read("status", 2, 20..30)
        "ledger".read("status", 3, 40..50)
        "fraud".read("status", 3, 20..30)
        "fraud".read("status", 2, 40..50)
    })
    show("answer before question: the auditor sees the reply but not what caused it", history {
        "agent".write("question", 1, 0..10)
        "merchant".read("question", 1, 20..30)
        "merchant".write("answer", 2, 40..50)
        "auditor".read("answer", 2, 60..70)
        "auditor".read("question", null, 80..90)
    })
    show("own write missing: checkout can't see its own debit", history {
        "checkout".write("balance", 70, 0..10)
        "checkout".read("balance", null, 20..30)
    })
}

/**
 * Write your own history here, then run with -Pargs=mine. The Try it asks for one that is causal but
 * not sequential. Each process's bars must not overlap; each write to a key writes a new value.
 */
fun mine(): History = history {
    "checkout".write("balance", 70, 0..10)
    "ledger".read("balance", 70, 20..30)
}

private val names = mapOf(
    Model.LINEARIZABLE to "linearizable",
    Model.SEQUENTIAL to "sequential",
    Model.CAUSAL to "causal",
    Model.READ_YOUR_WRITES to "read-your-writes",
    Model.MONOTONIC_READS to "monotonic-reads",
    Model.EVENTUAL to "eventual",
)

private fun show(title: String, h: History) {
    println(title)
    for (p in h.processes) {
        val ops = h.of(p).joinToString("   ") { op ->
            val what = if (op.kind == Kind.WRITE) "w(${op.key},${op.value})" else "r(${op.key})=${op.value ?: "-"}"
            "%-14s %2d-%-2d".format(what, op.start, op.end)
        }
        println("  %-9s %s".format(p, ops))
    }
    val got = classify(h)
    println("  " + Model.entries.joinToString("  ") { "${names.getValue(it)} ${if (it in got) "yes" else "no"}" })
    val witness = when {
        Model.LINEARIZABLE in got -> Search.legalOrder(h.ops, ::realTime)
        Model.SEQUENTIAL in got -> Search.legalOrder(h.ops, ::programOrder)
        else -> null
    }
    if (witness != null) {
        println("  one order that explains it: " + witness.joinToString(", ") {
            if (it.kind == Kind.WRITE) "${it.process} w(${it.key},${it.value})" else "${it.process} r(${it.key})=${it.value ?: "-"}"
        })
    }
    println()
}
