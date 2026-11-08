package sfz.derive.l05

/** One account where the live view and the recomputed view disagree. A side that has no row is null. */
data class Drift(val account: String, val live: Long?, val expected: Long?) {
    /** How far the live view is off: live minus expected, with a missing row counted as 0. */
    val delta: Long get() = (live ?: 0L) - (expected ?: 0L)
}

/**
 * Exercise 1. Recompute the balances view from the log, from offset 0: the sum of the postings
 * of each account. This is the same derivation the live consumer runs, as a pure function of an
 * immutable log, so it gives the same answer every time it runs.
 */
fun recompute(log: List<Posting>): Map<String, Long> {
    val view = sortedMapOf<String, Long>()
    for (p in log) view[p.account] = (view[p.account] ?: 0L) + p.cents   // a fold: no side effects
    return view
}

/**
 * Exercise 2. Compare a live view with the recomputed one, key by key. Return one [Drift] for
 * every account whose values differ or that is missing on one side, sorted by account.
 */
fun diff(live: Map<String, Long>, expected: Map<String, Long>): List<Drift> =
    (live.keys + expected.keys).toSortedSet()
        .filter { live[it] != expected[it] }                         // a missing row is a difference too
        .map { Drift(it, live[it], expected[it]) }
