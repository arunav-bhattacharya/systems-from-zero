package sfz.batch.l13.demo

import java.time.LocalDate
import kotlin.random.Random

/**
 * A small copy of the lab's model for the demos: a warehouse of day partitions, the daily-totals
 * pipeline (extract 5 min, load 10 min, report 5 min) and a runner with retries on virtual time.
 */
class Warehouse {
    val tables = mutableMapOf<String, MutableMap<LocalDate, List<Long>>>()
    fun read(t: String, d: LocalDate) = tables[t]?.get(d) ?: emptyList()
    fun append(t: String, d: LocalDate, rows: List<Long>) { val m = tables.getOrPut(t) { sortedMapOf() }; m[d] = (m[d] ?: emptyList()) + rows }
    fun overwrite(t: String, d: LocalDate, rows: List<Long>) { tables.getOrPut(t) { sortedMapOf() }[d] = rows }
    fun total(t: String) = tables[t]?.values?.sumOf { it.sum() } ?: 0L
}

fun payments(day: LocalDate): List<Long> {
    val rnd = Random(day.toEpochDay())
    return List(200 + rnd.nextInt(100)) { 100L + rnd.nextLong(50_000) }
}

class Crashed : RuntimeException()

/** The load step, two ways. */
val append = { w: Warehouse, d: LocalDate -> w.append("daily_totals", d, listOf(w.read("staging", d).sum())) }
val overwrite = { w: Warehouse, d: LocalDate -> w.overwrite("daily_totals", d, listOf(w.read("staging", d).sum())) }

/**
 * Runs extract, load, report for [day] from [start]; [crashes] says how many load attempts crash
 * after writing. Up to 2 retries, 5 minutes apart. Calls [log] with each event. Returns the end minute.
 */
fun runDay(w: Warehouse, day: LocalDate, load: (Warehouse, LocalDate) -> Unit, crashes: Int, start: Long = 0, log: (String) -> Unit = {}): Long {
    var clock = start
    clock += 5
    w.overwrite("staging", day, payments(day))
    log("minute %3d  extract   attempt 1: staging has ${w.read("staging", day).size} payments, ok".format(clock))
    var attempt = 0
    while (true) {
        attempt++
        clock += 10
        load(w, day)
        val rows = w.read("daily_totals", day).size
        if (attempt <= crashes) {
            log("minute %3d  load      attempt $attempt: wrote its total, daily_totals now has $rows row(s), then the worker died".format(clock))
            if (attempt > 2) { log("minute %3d  load      out of retries: FAILED".format(clock)); return clock }
            clock += 5
            log("minute %3d  scheduler retries load after 5 minutes".format(clock))
            continue
        }
        log("minute %3d  load      attempt $attempt: wrote its total, daily_totals now has $rows row(s), ok".format(clock))
        break
    }
    clock += 5
    w.overwrite("reports", day, w.read("daily_totals", day))
    log("minute %3d  report    attempt 1: reports the day as %,d cents".format(clock, w.read("reports", day).sum()))
    return clock
}
