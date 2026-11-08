package sfz.batch.l13.demo

import java.time.LocalDate
import kotlin.random.Random

/**
 * One night where the load task's worker dies right after it wrote its result, run with an
 * appending load and with an overwriting load. Then 90 nights with random crashes of that kind.
 */
fun main() {
    val day = LocalDate.of(2026, 11, 6)
    for ((name, load) in listOf("append (INSERT INTO)" to append, "overwrite the partition" to overwrite)) {
        val w = Warehouse()
        println("load = $name")
        runDay(w, day, load, crashes = 1) { println("  $it") }
        println("  the source says %,d cents".format(payments(day).sum()))
    }

    val days = (0 until 90).map { LocalDate.of(2026, 8, 9).plusDays(it.toLong()) }
    val rnd = Random(7)
    val crashes = days.associateWith { var n = 0; while (n < 2 && rnd.nextDouble() < 0.2) n++; n }
    val truth = days.sumOf { payments(it).sum() }
    println("90 nights, each load crashing after its write with chance 20% (sometimes twice): ${crashes.values.count { it > 0 }} nights hit")
    for ((name, load) in listOf("append" to append, "overwrite" to overwrite)) {
        val w = Warehouse()
        days.forEach { runDay(w, it, load, crashes.getValue(it)) }
        val wrong = days.count { w.read("daily_totals", it) != listOf(payments(it).sum()) }
        println("  %-9s total %,15d cents, %+.1f%% against the source, %d wrong days".format(name, w.total("daily_totals"), 100.0 * (w.total("daily_totals") - truth) / truth, wrong))
    }
}
