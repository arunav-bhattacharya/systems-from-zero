package sfz.repl.l05.demo

/**
 * Three regions replicate all-to-all. eu inserts payment pay-81723; us receives it and captures it;
 * ap's link from eu is slow, so the capture overtakes the insert on its way to ap.
 *
 * One-way delays (ms): eu->us 40, us->eu 40, us->ap 30, ap->us 30, eu->ap 150, ap->eu 150.
 * Three ways ap can treat an update for a row it doesn't have yet.
 */
private val delay = mapOf(
    "eu" to "us" to 40L, "us" to "eu" to 40L, "us" to "ap" to 30L,
    "ap" to "us" to 30L, "eu" to "ap" to 150L, "ap" to "eu" to 150L,
)

/** A replicated change: the row it sets, its origin's timestamp, and what its origin had applied. */
private data class Change(
    val id: String, val kind: String, val status: String, val ts: Long, val seen: Map<String, Int>,
)

private class Node(val name: String, val mode: String) {
    var row: Change? = null
    val applied = mutableMapOf<String, Int>() // per origin: how many of its changes are applied here
    private val held = mutableListOf<Change>()

    private fun origin(c: Change) = c.id.substringBefore(':')

    fun receive(c: Change, now: Long) {
        when (mode) {
            "discard" -> // pgactive's documented default: an UPDATE for a missing row is discarded
                if (c.kind == "UPDATE" && row == null) println("  t=%-3d %s discards %s %s: no such row".format(now, name, c.kind, c.status))
                else apply(c, now)
            "timestamps" -> // keep whichever version has the newer timestamp, inserts included
                if (row == null || c.ts > row!!.ts) apply(c, now)
                else println("  t=%-3d %s ignores %s %s: ts %d < %d".format(now, name, c.kind, c.status, c.ts, row!!.ts))
            "causal" -> { // hold a change until everything its origin had applied is applied here
                held += c
                var ready = held.firstOrNull { h -> h.seen.all { (o, n) -> (applied[o] ?: 0) >= n } }
                if (ready == null) println("  t=%-3d %s holds %s %s: it needs %s first".format(now, name, c.kind, c.status, c.seen))
                while (ready != null) {
                    held -= ready
                    apply(ready, now)
                    ready = held.firstOrNull { h -> h.seen.all { (o, n) -> (applied[o] ?: 0) >= n } }
                }
            }
        }
    }

    /** A write made here. Under timestamps it goes through the same rule as everyone else's. */
    fun local(c: Change, now: Long) = if (mode == "timestamps") receive(c, now) else apply(c, now)

    fun apply(c: Change, now: Long) {
        row = c
        applied[origin(c)] = (applied[origin(c)] ?: 0) + 1
        println("  t=%-3d %s applies %s %s".format(now, name, c.kind, c.status))
    }
}

private fun run(mode: String, usClockMs: Long) {
    println("-- $mode${if (usClockMs != 0L) ", us clock ${usClockMs} ms off" else ""} --")
    val nodes = listOf("eu", "us", "ap").associateWith { Node(it, mode) }
    val events = sortedMapOf<Long, MutableList<() -> Unit>>()
    fun at(t: Long, f: () -> Unit) = events.getOrPut(t) { mutableListOf() }.add(f)
    fun send(from: String, c: Change, now: Long) {
        for (to in nodes.keys) if (to != from) at(now + delay.getValue(from to to)) { nodes.getValue(to).receive(c, now + delay.getValue(from to to)) }
    }

    val insert = Change("eu:1", "INSERT", "AUTHORIZED", 0, emptyMap())
    at(0) { nodes.getValue("eu").local(insert, 0); send("eu", insert, 0) }
    at(45) { // us captures right after it has the insert; its clock may be off
        val capture = Change("us:1", "UPDATE", "CAPTURED", 45 + usClockMs, mapOf("eu" to 1))
        nodes.getValue("us").local(capture, 45)
        send("us", capture, 45)
    }
    while (events.isNotEmpty()) {
        val t = events.firstKey()
        events.remove(t)!!.forEach { it() }
    }
    println("  final: " + nodes.values.joinToString("  ") { "${it.name}=${it.row?.status}" })
    println()
}

fun main() {
    run("discard", 0)
    run("timestamps", -60)
    run("causal", 0)
}
