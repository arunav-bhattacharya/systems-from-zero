package sfz.batch.l13

import java.time.LocalDate

enum class TaskState { SUCCESS, FAILED, UPSTREAM_FAILED }

/** One run of a DAG for one logical date, in virtual minutes. */
data class RunResult(
    val logicalDate: LocalDate,
    val states: Map<String, TaskState>,
    /** Attempts per task that ran; a task that never ran has 0. */
    val attempts: Map<String, Int>,
    val startMinute: Long,
    val endMinute: Long,
)

/**
 * Lesson batch-13: a tiny orchestrator on virtual time. Within one run, tasks run one at a time in
 * topological order. A failed attempt is retried up to [maxRetries] times, [retryDelayMinutes] after
 * it failed.
 */
class DagRunner(val maxRetries: Int = 2, val retryDelayMinutes: Long = 5) {

    /**
     * Exercise 2. Runs [dag] once for [logicalDate], starting at [startMinute].
     *
     * - Tasks run in [Dag.topologicalOrder]. A task whose dependencies didn't all succeed doesn't
     *   run: it is UPSTREAM_FAILED, with 0 attempts.
     * - Each attempt advances the clock by the task's minutes and calls its action with
     *   `RunContext(logicalDate, attempt, warehouse)`, attempt counting from 1. An action that
     *   throws fails the attempt.
     * - After a failed attempt, if fewer than [maxRetries] retries were used, wait
     *   [retryDelayMinutes] and try again. Otherwise the task is FAILED.
     * - The result's end minute is the clock when the last task finished or gave up.
     */
    fun run(dag: Dag, logicalDate: LocalDate, warehouse: Warehouse, startMinute: Long = 0): RunResult {
        var clock = startMinute
        val states = linkedMapOf<String, TaskState>()
        val attempts = linkedMapOf<String, Int>()
        for (task in dag.topologicalOrder()) {
            if (task.deps.any { states[it] != TaskState.SUCCESS }) {
                states[task.id] = TaskState.UPSTREAM_FAILED       // never started: nothing to retry
                attempts[task.id] = 0
                continue
            }
            var attempt = 0
            while (true) {
                attempt++
                clock += task.minutes
                val ok = runCatching { task.action(RunContext(logicalDate, attempt, warehouse)) }.isSuccess
                if (ok) {
                    states[task.id] = TaskState.SUCCESS
                    break
                }
                if (attempt > maxRetries) {                        // the first attempt plus maxRetries retries
                    states[task.id] = TaskState.FAILED
                    break
                }
                clock += retryDelayMinutes
            }
            attempts[task.id] = attempt
        }
        return RunResult(logicalDate, states, attempts, startMinute, clock)
    }

    /**
     * Exercise 3. A backfill: one run of [dag] per day in [days], at most [maxActiveRuns] at a time.
     *
     * Model it with [maxActiveRuns] slots that all start free at minute 0. Take the days oldest first,
     * or newest first if [runBackwards]. Give each day to the slot that is free earliest (the lowest
     * slot number on a tie), run it there with [run], and the slot is free again at the run's end.
     * Return the results in the order the runs were started.
     */
    fun backfill(dag: Dag, days: List<LocalDate>, warehouse: Warehouse, maxActiveRuns: Int, runBackwards: Boolean = false): List<RunResult> {
        require(maxActiveRuns >= 1)
        val freeAt = LongArray(maxActiveRuns)                       // when each slot can start its next run
        val order = if (runBackwards) days.sortedDescending() else days.sorted()
        return order.map { day ->
            val slot = freeAt.indices.minBy { freeAt[it] }          // minBy keeps the first, the lowest slot, on a tie
            run(dag, day, warehouse, startMinute = freeAt[slot]).also { freeAt[slot] = it.endMinute }
        }
    }
}
