package sfz.found.l06

// Reference answers for ErrorBudget.kt.

private const val MINUTES_PER_DAY = 1_440

fun budgetMinutes(slo: Double, windowDays: Int = 30): Double = (1.0 - slo) * windowDays * MINUTES_PER_DAY

fun burnRate(errorRatio: Double, slo: Double): Double = errorRatio / (1.0 - slo)

fun budgetSpent(burnRate: Double, minutes: Double, windowDays: Int = 30): Double =
    burnRate * minutes / (windowDays * MINUTES_PER_DAY.toDouble())

fun errorRatio(series: List<Minute>, end: Int, windowMinutes: Int): Double {
    var bad = 0L
    var total = 0L
    for (t in maxOf(0, end - windowMinutes + 1)..end) {       // the window ends with minute `end`
        bad += series[t].bad
        total += series[t].total
    }
    return if (total == 0L) 0.0 else bad.toDouble() / total
}

fun replay(series: List<Minute>, slo: Double, rules: List<Rule> = WORKBOOK_RULES): List<Alert> {
    // running sums make every window O(1); the history can be weeks of minutes
    val badSum = LongArray(series.size + 1)
    val totalSum = LongArray(series.size + 1)
    for (t in series.indices) {
        badSum[t + 1] = badSum[t] + series[t].bad
        totalSum[t + 1] = totalSum[t] + series[t].total
    }
    fun ratio(end: Int, window: Int): Double {
        val from = maxOf(0, end - window + 1)
        val total = totalSum[end + 1] - totalSum[from]
        return if (total == 0L) 0.0 else (badSum[end + 1] - badSum[from]).toDouble() / total
    }

    val budget = 1.0 - slo
    val alerts = ArrayList<Pair<Int, Alert>>()
    rules.forEachIndexed { order, rule ->
        val threshold = rule.burnRate * budget
        var firedAt: Int? = null
        for (t in series.indices) {
            // the long window says "this matters"; the short one says "it is still happening"
            val firing = ratio(t, rule.longMinutes) >= threshold && ratio(t, rule.shortMinutes) >= threshold
            if (firing && firedAt == null) firedAt = t
            if (!firing && firedAt != null) {
                alerts += order to Alert(rule.name, rule.action, firedAt, t)
                firedAt = null
            }
        }
        firedAt?.let { alerts += order to Alert(rule.name, rule.action, it, null) }
    }
    return alerts.sortedWith(compareBy({ it.second.firedAt }, { it.first })).map { it.second }
}
