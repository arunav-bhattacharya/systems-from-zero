package sfz.cons.l01.demo

/**
 * Lesson cons-01: the choice CAP describes, on three replicas of one balance (eu, us, apac).
 *   ./gradlew :sim:demo -Pmain=sfz.cons.l01.demo.CapDemoKt -q
 *
 * One-way delays: eu-us 40 ms, us-apac 60 ms, eu-apac 80 ms. A local read or write takes 1 ms.
 * From 1,000 ms to 3,000 ms eu is cut off from both others: a network partition.
 * "available": every replica answers from its own copy and sends writes on later (last write wins).
 * "consistent": a request must reach a majority (2 of 3) before it is answered, or it is refused
 * after a 500 ms timeout.
 */
fun main() {
    for (consistent in listOf(false, true)) run(consistent)
}

private val oneWay = mapOf(
    setOf("eu", "us") to 40L, setOf("us", "apac") to 60L, setOf("eu", "apac") to 80L,
)
private val replicas = listOf("eu", "us", "apac")
private const val CUT = 1_000L
private const val HEAL = 3_000L

private fun cutOff(a: String, b: String, t: Long) = t in CUT until HEAL && (a == "eu" || b == "eu") && a != b

private data class Versioned(val version: Long, val value: Int?)

private class Request(val at: Long, val replica: String, val client: String, val write: Int?)

private fun run(consistent: Boolean) {
    println(if (consistent) "consistent: a request must reach a majority (2 of 3 replicas) first"
    else "available: every replica answers from its own copy")
    val script = listOf(
        Request(0, "eu", "checkout", 70),
        Request(100, "us", "ledger", null),
        Request(1_100, "eu", "checkout", 40),
        Request(1_200, "us", "ledger", null),
        Request(1_300, "apac", "fraud", 55),
        Request(3_500, "eu", "checkout", null),
        Request(3_500, "us", "ledger", null),
    )
    val copies = replicas.associateWith { mutableListOf<Pair<Long, Versioned>>() }   // (time it arrives, value)
    fun copyAt(r: String, t: Long) = copies.getValue(r).filter { it.first <= t }.maxByOrNull { it.second.version }?.second
        ?: Versioned(0, null)
    val ops = mutableListOf<Op>()
    var said1000 = false
    var said3000 = false
    for (req in script) {
        if (!said1000 && req.at >= CUT) { println("  %5d ms  eu is cut off from us and apac".format(CUT)); said1000 = true }
        if (!said3000 && req.at >= HEAL) { println("  %5d ms  the network heals".format(HEAL)); said3000 = true }
        val others = replicas.filter { it != req.replica }
        val reachable = others.filter { !cutOff(req.replica, it, req.at) }
        val what = if (req.write != null) "writes balance=${req.write}" else "reads  balance"
        val prefix = "  %5d ms  %-5s %-9s %-19s".format(req.at, req.replica, req.client, what)
        if (!consistent) {
            val done = req.at + 1
            val value = if (req.write != null) {
                val v = Versioned(req.at, req.write)                      // last write wins on the request time
                copies.getValue(req.replica) += done to v
                for (o in others) {                                       // sent on now, or as soon as the link is back
                    val leaves = if (cutOff(req.replica, o, req.at)) HEAL else req.at
                    copies.getValue(o) += (leaves + oneWay.getValue(setOf(req.replica, o))) to v
                }
                req.write
            } else copyAt(req.replica, req.at).value
            println(prefix + (if (req.write != null) "ok" else "${value ?: "-"}").padEnd(5) + " after 1 ms")
            ops += Op(ops.size, req.client, if (req.write != null) Kind.WRITE else Kind.READ, "balance", value, req.at, done)
        } else {
            if (reachable.isEmpty()) {
                println(prefix + "refused after 500 ms: can't reach a majority")
                continue                                                  // nothing was applied anywhere
            }
            val nearest = reachable.minBy { oneWay.getValue(setOf(req.replica, it)) }
            val rtt = 2 * oneWay.getValue(setOf(req.replica, nearest))
            val done = req.at + 1 + rtt
            val quorum = listOf(req.replica, nearest)
            val latest = quorum.map { copyAt(it, req.at) }.maxBy { it.version }
            val value = if (req.write != null) {
                val v = Versioned(latest.version + 1, req.write)
                for (r in quorum) copies.getValue(r) += req.at to v
                for (o in others - nearest) {
                    val leaves = if (cutOff(req.replica, o, req.at)) HEAL else req.at
                    copies.getValue(o) += (leaves + oneWay.getValue(setOf(req.replica, o))) to v
                }
                req.write
            } else latest.value
            println(prefix + (if (req.write != null) "ok" else "${value ?: "-"}").padEnd(5) + " after ${1 + rtt} ms (via $nearest)")
            ops += Op(ops.size, req.client, if (req.write != null) Kind.WRITE else Kind.READ, "balance", value, req.at, done)
        }
    }
    val got = classify(History(ops))
    println("  the history of answered requests: linearizable ${if (Model.LINEARIZABLE in got) "yes" else "no"}, " +
        "eventual ${if (Model.EVENTUAL in got) "yes" else "no"}")
    println()
}
