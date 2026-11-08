package sfz.found.l06.demo

// Replays an incident against a 99.9% SLO and the Workbook's burn-rate alerts, in virtual time.
// Run from the labs folder:
//   ./gradlew :sim:demo -Pmain=sfz.found.l06.demo.BurnRateDemoKt --console=plain -q
//   ./gradlew :sim:demo -Pmain=sfz.found.l06.demo.BurnRateDemoKt --console=plain -q -Pargs='100 10'
// The arguments are the share of requests that fail, in percent, and how many minutes it lasts.
// (A self-contained copy of the lab's logic: demos can't see src/main.)

const val SLO = 0.999
const val DAY = 1_440
const val PER_MINUTE = 10_000L

class Rule(val name: String, val long: Int, val short: Int, val burn: Double, val action: String)

val RULES = listOf(
    Rule("fast burn", 60, 5, 14.4, "PAGE"),
    Rule("medium burn", 360, 30, 6.0, "PAGE"),
    Rule("slow burn", 3 * DAY, 360, 1.0, "TICKET"),
    Rule("naive 10 min", 10, 10, 1.0, "PAGE"),
)

fun main(args: Array<String>) {
    val percent = args.getOrNull(0)?.toDouble() ?: 2.0
    val minutes = args.getOrNull(1)?.toInt() ?: 100
    val start = 3 * DAY                                   // three clean days first, so every window is full
    val length = start + minutes + 3 * DAY
    val bad = LongArray(length) { t -> if (t in start until start + minutes) Math.round(PER_MINUTE * percent / 100) else 0L }
    val badSum = LongArray(length + 1).also { for (t in 0 until length) it[t + 1] = it[t] + bad[t] }
    fun ratio(end: Int, window: Int): Double {
        val from = maxOf(0, end - window + 1)
        return (badSum[end + 1] - badSum[from]).toDouble() / ((end + 1 - from) * PER_MINUTE)
    }

    val budget = 1 - SLO
    val burn = percent / 100 / budget
    println("SLO 99.9%% over 30 days: the budget is %.1f minutes of full outage, or 0.1%% of requests".format(budget * 30 * DAY))
    println("incident: %.2f%% of requests fail for %d minutes, a burn rate of %.1f".format(percent, minutes, burn))
    println("the incident uses %.2f%% of the month's budget".format(100 * burn * minutes / (30.0 * DAY)))
    println()
    println("minutes after the start of the incident:")
    val events = ArrayList<Pair<Int, String>>()
    for (rule in RULES) {
        val threshold = rule.burn * budget
        var firing = false
        for (t in 0 until length) {
            val now = ratio(t, rule.long) >= threshold && ratio(t, rule.short) >= threshold
            if (now && !firing) {
                val spent = 100 * burn * minOf(t - start + 1, minutes) / (30.0 * DAY)
                events += (t - start) to "%-6s %-12s fires   (budget spent so far %.2f%%)".format(rule.action, rule.name, spent)
            }
            if (!now && firing) events += (t - start) to "       %-12s clears".format(rule.name)
            firing = now
        }
    }
    if (events.isEmpty()) println("  no alert fires")
    events += minutes to "       (errors stop at the start of this minute)"
    for ((t, text) in events.sortedBy { it.first }) println("%7d  %s".format(t, text))
}
