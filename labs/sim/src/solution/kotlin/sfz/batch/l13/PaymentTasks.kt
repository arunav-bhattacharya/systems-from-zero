package sfz.batch.l13

import java.time.LocalDate
import kotlin.random.Random

/** Given: the payments system of record. The same day always has the same payments. */
object Source {
    /** The day's captured payments, in cents: 200 to 299 of them. */
    fun payments(day: LocalDate): List<Long> {
        val rnd = Random(day.toEpochDay())
        return List(200 + rnd.nextInt(100)) { 100L + rnd.nextLong(50_000) }
    }

    fun total(day: LocalDate): Long = payments(day).sum()
}

/** Given: a task that did its writes and then died before it could report success. */
class TaskCrashed(message: String) : RuntimeException(message)

/**
 * Given: which attempts crash. `plan[task to day] = n` makes the first n attempts of that task on
 * that day crash after their writes. The worker died, the network dropped the "done" message, the
 * pod was preempted: the orchestrator only sees a failed attempt.
 */
class Faults(private val plan: Map<Pair<String, LocalDate>, Int>) {
    fun afterWrite(task: String, ctx: RunContext) {
        if (ctx.attempt <= (plan[task to ctx.logicalDate] ?: 0)) {
            throw TaskCrashed("$task for ${ctx.logicalDate}, attempt ${ctx.attempt}: crashed after its writes")
        }
    }

    /** How many days have at least one crash planned for [task]. */
    fun daysHit(task: String): Int = plan.filter { it.key.first == task && it.value > 0 }.size

    companion object {
        val NONE = Faults(emptyMap())

        /** On each day, each of extract and load crashes once with chance [rate], and a second time with chance [rate] again. */
        fun random(seed: Long, days: List<LocalDate>, rate: Double = 0.2): Faults {
            val rnd = Random(seed)
            val plan = mutableMapOf<Pair<String, LocalDate>, Int>()
            for (d in days) for (t in listOf("extract", "load")) {
                var n = 0
                while (n < 2 && rnd.nextDouble() < rate) n++
                if (n > 0) plan[t to d] = n
            }
            return Faults(plan)
        }
    }
}

/**
 * Lesson batch-13: the daily-totals pipeline. `extract` copies the day's payments into the
 * `staging` table, `load` writes the day's total into `daily_totals`, and `report` reads it.
 */
object PaymentTasks {
    /** Given: copies the logical date's payments into `staging`, replacing the partition. */
    fun extract(ctx: RunContext) = ctx.warehouse.overwrite("staging", ctx.logicalDate, Source.payments(ctx.logicalDate))

    /** Given, and not idempotent: appends the day's total, so a second attempt adds a second row. */
    fun appendDailyTotal(ctx: RunContext) {
        val total = ctx.warehouse.read("staging", ctx.logicalDate).sum()
        ctx.warehouse.append("daily_totals", ctx.logicalDate, listOf(total))
    }

    /**
     * Given, and wrong in a different way: totals the newest staging partition instead of its own
     * logical date's. Run on schedule it gives the right answer; in a backfill it doesn't.
     */
    fun latestDailyTotal(ctx: RunContext) {
        val newest = ctx.warehouse.partitions("staging").last()
        ctx.warehouse.overwrite("daily_totals", ctx.logicalDate, listOf(ctx.warehouse.read("staging", newest).sum()))
    }

    /**
     * Exercise 4. The idempotent load: read the staging partition of the run's own logical date, and
     * replace that date's `daily_totals` partition with its total, as one row. Running it twice
     * leaves the same table as running it once.
     */
    fun overwriteDailyTotal(ctx: RunContext) {
        // keyed by the logical date, never by "now" or "the newest partition"
        val total = ctx.warehouse.read("staging", ctx.logicalDate).sum()
        // replace the partition: a retry or a rerun writes the same single row again
        ctx.warehouse.overwrite("daily_totals", ctx.logicalDate, listOf(total))
    }

    /** Given: the pipeline extract (5 min) -> load (10 min) -> report (5 min), with [load] as the load step and [faults] injected. */
    fun dag(load: (RunContext) -> Unit, faults: Faults = Faults.NONE): Dag {
        fun task(id: String, deps: List<String>, minutes: Long, action: (RunContext) -> Unit) =
            Task(id, deps, minutes) { ctx -> action(ctx); faults.afterWrite(id, ctx) }
        return Dag(listOf(
            task("extract", emptyList(), 5, ::extract),
            task("load", listOf("extract"), 10, load),
            task("report", listOf("load"), 5) { ctx -> ctx.warehouse.overwrite("reports", ctx.logicalDate, ctx.warehouse.read("daily_totals", ctx.logicalDate)) },
        ))
    }
}
