package sfz.stream.l04.demo

/**
 * Lesson stream-04, Try it 4: the fraud team wants a count for the 10:00-10:05 window early, not
 * 5 minutes plus grace later. The window fires early every minute of processing time, fires again
 * when the watermark passes its end, and once more for each late event inside the grace period.
 * What each firing sends downstream depends on the accumulation mode.
 */

data class Firing(val at: String, val why: String, val newEvents: Int)

fun main() {
    // what the window had seen at each firing (events that arrived since the previous firing)
    val firings = listOf(
        Firing("10:01", "early (1 min of processing time)", 14),
        Firing("10:02", "early", 11),
        Firing("10:03", "early", 9),
        Firing("10:04", "early", 12),
        Firing("10:05", "on time: the watermark passed 10:05", 10),
        Firing("10:06", "late event, inside the grace period", 1),
    )
    println("%-6s %-38s %10s %13s  %s".format("fires", "why", "discarding", "accumulating", "accumulating and retracting"))
    var total = 0
    for (f in firings) {
        val before = total
        total += f.newEvents
        val retracting = if (before == 0) "+$total" else "-$before, +$total"
        println("%-6s %-38s %10d %13d  %s".format(f.at, f.why, f.newEvents, total, retracting))
    }
    println()
    println("a sink that adds up what it receives gets the right total from discarding: ${firings.sumOf { it.newEvents }}")
    println("a sink that adds up accumulating panes counts the same events again: ${firings.runningFold(0) { a, f -> a + f.newEvents }.drop(1).sum()}")
    println("a sink that upserts by window keeps the last accumulating pane: $total")
}
