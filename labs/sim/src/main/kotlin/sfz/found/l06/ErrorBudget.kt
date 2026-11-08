package sfz.found.l06

// Error budgets and burn-rate alerts. Read Traffic.kt first: it has the data types and the rules.
// Time is virtual: a history is a list of minutes, and "now" is an index into it.

/**
 * The error budget as minutes of full outage: `(1 - slo) x days x 1,440`.
 * 99.9% over 30 days is 43.2 minutes.
 */
fun budgetMinutes(slo: Double, windowDays: Int = 30): Double {
    TODO("(1 - slo) x windowDays x 1440")
}

/**
 * How fast an error ratio spends the budget: `errorRatio / (1 - slo)`. At a burn rate of 1 the budget
 * lasts exactly the SLO window; at 1,000 (everything failing, for a 99.9% SLO) it lasts 1/1,000 of it.
 */
fun burnRate(errorRatio: Double, slo: Double): Double {
    TODO("errorRatio / (1 - slo)")
}

/** The share of the whole window's budget used by burning at [burnRate] for [minutes]. */
fun budgetSpent(burnRate: Double, minutes: Double, windowDays: Int = 30): Double {
    TODO("burnRate x minutes / (windowDays x 1440)")
}

/**
 * The error ratio, bad / total, over the [windowMinutes] minutes that end with minute [end], counting
 * [end] itself: minutes `end - windowMinutes + 1 .. end`. Near the start of the history, use the minutes
 * that exist. No traffic at all counts as 0.0.
 */
fun errorRatio(series: List<Minute>, end: Int, windowMinutes: Int): Double {
    TODO("sum bad and total over the window, then divide")
}

/**
 * Replays [series] one minute at a time. At the end of each minute t, a rule is firing when
 * BOTH `errorRatio(series, t, rule.longMinutes)` and `errorRatio(series, t, rule.shortMinutes)` are at
 * least `rule.burnRate x (1 - slo)`.
 *
 * Returns one [Alert] per firing episode of each rule: `firedAt` is the first minute it fires,
 * `resolvedAt` the first minute after that when it no longer fires (null if it is still firing at the end).
 * Sort the result by `firedAt`, then by the rule's position in [rules].
 */
fun replay(series: List<Minute>, slo: Double, rules: List<Rule> = WORKBOOK_RULES): List<Alert> {
    TODO("for each rule, walk the minutes, open an episode when it starts firing and close it when it stops")
}
