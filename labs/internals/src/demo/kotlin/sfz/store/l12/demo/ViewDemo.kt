package sfz.store.l12.demo

import sfz.store.l12.Change
import sfz.store.l12.Deleted
import sfz.store.l12.IncrementalView
import sfz.store.l12.Inserted
import sfz.store.l12.Payment
import sfz.store.l12.PaymentTable
import sfz.store.l12.Work
import sfz.store.l12.fullRecompute
import kotlin.random.Random

/**
 * Lesson store-12, Try it: the per-merchant view (count, sum, min) over 20,000 payments, kept up to date
 * through 1,000 changes two ways, then through one batch that deletes most of the table. It counts rows
 * touched (base rows read plus view rows written) rather than time, so the numbers are the same on every
 * machine. It runs the lab's reference solution.
 *
 *   ./gradlew :internals:demo -Pmain=sfz.store.l12.demo.ViewDemoKt --console=plain -q
 */
fun main() {
    val rnd = Random(2026)
    val table = PaymentTable()
    val live = ArrayList<Payment>()
    var nextId = 1L
    fun newPayment() = Payment(nextId++, "M-%04d".format(rnd.nextInt(200)), 1L + rnd.nextInt(100_000))
    repeat(20_000) { val p = newPayment(); table.apply(Inserted(p)); live += p }

    // 1. a normal stream: 1,000 changes, half inserts and half deletes of random payments
    val view = IncrementalView(table)
    val refreshEach = Work()
    var deletes = 0
    repeat(1_000) { i ->
        val change: Change = if (i % 2 == 0) Inserted(newPayment().also { live += it })
        else Deleted(live.removeAt(rnd.nextInt(live.size))).also { deletes++ }
        table.apply(change)
        view.apply(change)
        fullRecompute(table, refreshEach)
    }
    println("base table: %,d payments over 200 merchants".format(table.size))
    println("1,000 changes: 500 inserts, $deletes deletes, ${view.minRescans} of them removed a merchant's minimum")
    println()
    println("%-34s %15s %18s".format("strategy", "base rows read", "view rows written"))
    println("%-34s %,15d %,18d".format("full recompute after every change", refreshEach.baseRowsRead, refreshEach.viewRowsWritten))
    println("%-34s %,15d %,18d".format("incremental (delta rules)", view.work.baseRowsRead, view.work.viewRowsWritten))
    println("incremental touched %,d rows: %.3f%% of the recompute's %,d".format(
        view.work.rowsTouched, 100.0 * view.work.rowsTouched / refreshEach.rowsTouched, refreshEach.rowsTouched))

    // 2. a batch that deletes 90% of the table: one full recompute at the end, or a delta per change?
    val before = view.work.rowsTouched
    val rescansBefore = view.minRescans
    live.shuffle(rnd)
    val batch = live.take(live.size * 9 / 10)
    for (p in batch) { val change = Deleted(p); table.apply(change); view.apply(change) }
    val once = Work()
    fullRecompute(table, once)
    println()
    println("a batch deleting %,d payments (90%% of the table):".format(batch.size))
    println("  incremental, one delta per change: %,d rows touched (%,d min rescans)".format(
        view.work.rowsTouched - before, view.minRescans - rescansBefore))
    println("  one full recompute afterwards:     %,d rows touched".format(once.rowsTouched))
}
