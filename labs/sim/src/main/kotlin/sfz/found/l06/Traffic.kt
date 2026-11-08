package sfz.found.l06

import kotlin.math.roundToLong

// Finished: read it, don't change it. The same file is in src/solution.

/** One minute of a service's life: how many requests it answered and how many of those were bad. */
data class Minute(val total: Long, val bad: Long)

/** From [startMinute], for [minutes] minutes, a share [errorRatio] of requests fail. */
data class Incident(val startMinute: Int, val minutes: Int, val errorRatio: Double)

/**
 * A replayable history: [totalMinutes] minutes of steady traffic, [perMinute] requests each, with no
 * errors except during the [incidents]. Minute 0 is the first minute; one day is 1,440 minutes.
 */
fun traffic(totalMinutes: Int, vararg incidents: Incident, perMinute: Long = 10_000): List<Minute> =
    List(totalMinutes) { t ->
        val ratio = incidents.filter { t >= it.startMinute && t < it.startMinute + it.minutes }.sumOf { it.errorRatio }
        Minute(perMinute, (perMinute * ratio.coerceAtMost(1.0)).roundToLong())
    }

/** A paging rule: fire when the error ratio over BOTH windows is at least [burnRate] times the budget. */
data class Rule(val name: String, val longMinutes: Int, val shortMinutes: Int, val burnRate: Double, val action: Action)

enum class Action { PAGE, TICKET }

/** The multiwindow, multi-burn-rate alerts the Google SRE Workbook recommends for a 30-day SLO. */
val WORKBOOK_RULES = listOf(
    Rule("fast burn", longMinutes = 60, shortMinutes = 5, burnRate = 14.4, action = Action.PAGE),
    Rule("medium burn", longMinutes = 360, shortMinutes = 30, burnRate = 6.0, action = Action.PAGE),
    Rule("slow burn", longMinutes = 3 * 1_440, shortMinutes = 360, burnRate = 1.0, action = Action.TICKET),
)

/** The alert most teams start with: page when the last 10 minutes miss the SLO at all. */
val NAIVE_RULE = Rule("naive 10 min", longMinutes = 10, shortMinutes = 10, burnRate = 1.0, action = Action.PAGE)

/** One firing episode of a rule: it fired at the end of minute [firedAt] and stopped at [resolvedAt] (null: still firing). */
data class Alert(val rule: String, val action: Action, val firedAt: Int, val resolvedAt: Int?)
