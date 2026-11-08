package sfz.batch.l13

import java.time.LocalDate

/** What a task gets when it runs: the day it is for (its logical date), its attempt number, and the warehouse. */
data class RunContext(val logicalDate: LocalDate, val attempt: Int, val warehouse: Warehouse)

/**
 * One step of a pipeline. [deps] are the ids of the tasks that must succeed first. Every attempt
 * takes [minutes] of virtual time. [action] does the work and throws to fail the attempt.
 */
class Task(val id: String, val deps: List<String> = emptyList(), val minutes: Long, val action: (RunContext) -> Unit)

/** Lesson batch-13: a pipeline as a directed acyclic graph of tasks. */
class Dag(val tasks: List<Task>) {
    private val byId = tasks.associateBy { it.id }

    init {
        require(byId.size == tasks.size) { "task ids must be unique" }
        for (t in tasks) for (d in t.deps) require(d in byId) { "task ${t.id} depends on unknown task $d" }
    }

    fun task(id: String): Task = byId.getValue(id)

    /**
     * Exercise 1. The tasks in an order where every task comes after all of its [Task.deps]
     * (Kahn's algorithm). When several tasks are ready at once, take them in id order, so the order
     * is the same on every run. Throws [IllegalArgumentException] if the graph has a cycle.
     */
    fun topologicalOrder(): List<Task> {
        TODO("Exercise 1: Kahn's algorithm, ready tasks in id order; throw IllegalArgumentException on a cycle")
    }
}
