package sfz.batch.l13.demo

import java.time.LocalDate

/**
 * A year of history backfilled with the daily-totals pipeline (20 minutes a run), with Airflow's
 * `--max-active-runs` at 1, 4 and 16, oldest first and with `--run-backwards`. Then the same backfill
 * run a second time, the way `--reprocess-behavior completed` would, with each kind of load.
 */
fun main() {
    val days = (0 until 365).map { LocalDate.of(2025, 11, 7).plusDays(it.toLong()) }
    fun hours(m: Long) = "%.1f h".format(m / 60.0)
    println("365 daily runs of 20 minutes:")
    for (active in listOf(1, 4, 16)) {
        val (end, firstWeekDone) = backfill(days, active, backwards = false)
        val (endB, newestWeekDone) = backfill(days, active, backwards = true)
        println("  max active runs %2d: done after %7s; the newest week is ready after %7s, or %7s with run backwards".format(
            active, hours(end), hours(firstWeekDone), hours(newestWeekDone)))
        check(end == endB)
    }
    for ((name, load) in listOf("append" to append, "overwrite" to overwrite)) {
        val w = Warehouse()
        repeat(2) { days.forEach { runDay(w, it, load, crashes = 0) } }
        val truth = days.sumOf { payments(it).sum() }
        println("backfill run twice, load = %-9s total is %.2f times the source".format(name, w.total("daily_totals").toDouble() / truth))
    }
}

/** Returns when the whole backfill ends, and when the newest 7 days are all done, in minutes. */
private fun backfill(days: List<LocalDate>, active: Int, backwards: Boolean): Pair<Long, Long> {
    val freeAt = LongArray(active)
    val ends = mutableMapOf<LocalDate, Long>()
    for (d in if (backwards) days.reversed() else days) {
        val slot = freeAt.indices.minBy { freeAt[it] }
        freeAt[slot] += 20
        ends[d] = freeAt[slot]
    }
    return ends.values.max() to days.takeLast(7).maxOf { ends.getValue(it) }
}
