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
        // how many unfinished dependencies each task still waits for
        val waiting = tasks.associate { it.id to it.deps.size }.toMutableMap()
        val dependents = tasks.flatMap { t -> t.deps.map { it to t.id } }.groupBy({ it.first }, { it.second })
        val ready = sortedSetOf<String>().apply { addAll(waiting.filterValues { it == 0 }.keys) }
        val order = mutableListOf<Task>()
        while (ready.isNotEmpty()) {
            val id = ready.first()
            ready.remove(id)
            order += byId.getValue(id)
            for (next in dependents[id].orEmpty()) {
                waiting[next] = waiting.getValue(next) - 1
                if (waiting[next] == 0) ready += next
            }
        }
        // tasks never released are on a cycle (or wait on one)
        require(order.size == tasks.size) { "the graph has a cycle among ${tasks.map { it.id } - order.map { it.id }.toSet()}" }
        return order
    }
}
