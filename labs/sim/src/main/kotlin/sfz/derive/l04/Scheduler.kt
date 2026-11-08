package sfz.derive.l04

import kotlin.random.Random

/**
 * A seeded, deterministic scheduler (finished; nothing to write here).
 *
 * Each task is a block of code that calls `yield(Unit)` wherever another task may run in between:
 * a network round trip, a poll of a log. At every tick the scheduler picks one live task with its
 * seeded [Random] and runs it up to its next `yield`. The same seed gives the same interleaving,
 * so every count in the tests is exact and the same on every laptop.
 */
class Scheduler(seed: Long) {
    private val rnd = Random(seed)
    private val live = ArrayList<Iterator<Unit>>()

    /** Steps run so far: the simulation's clock. */
    var now = 0L
        private set

    /** Adds a task. It starts running at the next tick that picks it. */
    fun spawn(body: suspend SequenceScope<Unit>.() -> Unit) {
        live += iterator(body)
    }

    /** Runs until every task has finished. [maxSteps] guards against a simulation that never ends. */
    fun run(maxSteps: Long = 50_000_000) {
        while (live.isNotEmpty()) {
            check(now < maxSteps) { "the simulation did not finish in $maxSteps steps" }
            val i = rnd.nextInt(live.size)
            val task = live[i]
            if (task.hasNext()) {           // runs the task up to its next yield
                task.next()
            } else {                        // the task has finished: swap-remove it
                live[i] = live[live.size - 1]
                live.removeAt(live.size - 1)
            }
            now++
        }
    }
}

/** The value below which [p] of the [values] fall (nearest rank). */
fun percentile(values: List<Long>, p: Double): Long {
    if (values.isEmpty()) return 0
    val sorted = values.sorted()
    val rank = Math.ceil(p * sorted.size).toInt().coerceIn(1, sorted.size)
    return sorted[rank - 1]
}
