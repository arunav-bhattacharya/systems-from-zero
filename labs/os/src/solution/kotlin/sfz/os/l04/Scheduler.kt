package sfz.os.l04

/**
 * Linux's table from nice value to weight: `sched_prio_to_weight` in kernel/sched/core.c.
 * Nice 0 is 1024. Each step is about 1.25 times the next, which is the kernel's
 * "10% less CPU per nice level" rule. Written for you.
 */
object Nice {
    const val NICE_0 = 1024

    private val WEIGHTS = intArrayOf(
        /* -20 */ 88761, 71755, 56483, 46273, 36291,
        /* -15 */ 29154, 23254, 18705, 14949, 11916,
        /* -10 */ 9548, 7620, 6100, 4904, 3906,
        /*  -5 */ 3121, 2501, 1991, 1586, 1277,
        /*   0 */ 1024, 820, 655, 526, 423,
        /*   5 */ 335, 272, 215, 172, 137,
        /*  10 */ 110, 87, 70, 56, 45,
        /*  15 */ 36, 29, 23, 18, 15,
    )

    fun weight(nice: Int): Int {
        require(nice in -20..19) { "nice must be between -20 and 19, was $nice" }
        return WEIGHTS[nice + 20]
    }

    /**
     * The share of one CPU each task gets when every task is always runnable:
     * its weight divided by the sum of all the weights. Same order as [nices].
     */
    fun expectedShares(nices: List<Int>): List<Double> {
        val weights = nices.map { weight(it) }
        val total = weights.sum().toDouble()
        return weights.map { it / total }                  // share depends on the ratio, never on the absolute nice
    }
}

/**
 * A CPU-bound task: always runnable, never sleeps, like the `spin` loop in this lesson.
 *
 * @property sliceMs how long the task asks to run each time it gets the CPU (EEVDF's request size).
 *   The kernel's default is 3 ms on a machine with 8 or more CPUs.
 */
class Task(val name: String, val nice: Int = 0, val sliceMs: Double = 3.0) {
    val weight: Int = Nice.weight(nice)

    /** Virtual runtime in ms: real CPU time scaled by 1024 / weight. Heavy tasks' clocks run slow. */
    var vruntime = 0.0

    /** EEVDF only: the virtual time by which this task's current slice should be finished. */
    var deadline = 0.0

    /** Real CPU time this task has had, in ms. The simulator updates it. */
    var ranMs = 0.0

    override fun toString() = "Task($name, nice=$nice, vruntime=$vruntime, deadline=$deadline)"
}

/** A scheduling policy: which task runs next, for how long, and how to account for it afterwards. */
interface Scheduler {
    /** Called once with every task, before the first [pick]. */
    fun start(tasks: List<Task>) {}

    /** The task that runs next. Every task is runnable all the time. */
    fun pick(tasks: List<Task>): Task

    /** How long [task] runs once picked, before the scheduler decides again. */
    fun sliceFor(task: Task): Double

    /** Account for [ms] of real CPU time that [task] just used. */
    fun charge(task: Task, ms: Double, tasks: List<Task>)
}

/** One slice of time on the CPU. */
data class Run(val task: String, val startMs: Double, val ms: Double)

/** What happened on the CPU, with the numbers `getrusage` and `/proc/<pid>/schedstat` give you. Written for you. */
class Timeline(val runs: List<Run>, val totalMs: Double) {
    /** Fraction of the CPU [task] got. */
    fun share(task: String): Double = runs.filter { it.task == task }.sumOf { it.ms } / totalMs

    /** The task names of the first [n] slices, as one string of first letters: "ABAAAB". */
    fun order(n: Int): String = runs.take(n).joinToString("") { it.task.take(1) }

    /**
     * Back-to-back slices of the same task merged into one stretch: what the task sees as one turn on
     * the CPU. A task gets switched out once per stretch.
     */
    fun stretches(task: String): List<Run> {
        val merged = mutableListOf<Run>()
        for (r in runs) {
            val last = merged.lastOrNull()
            if (last != null && last.task == r.task) merged[merged.size - 1] = last.copy(ms = last.ms + r.ms)
            else merged += r
        }
        return merged.filter { it.task == task }
    }

    /** The longest time [task] waited between two of its turns: how long it was runnable but not running. */
    fun longestWait(task: String): Double =
        stretches(task).zipWithNext { a, b -> b.startMs - (a.startMs + a.ms) }.maxOrNull() ?: 0.0
}

/** One simulated CPU. Asks the scheduler for a task, runs it for its slice, charges it, repeats. Written for you. */
class Cpu(private val scheduler: Scheduler) {
    fun run(tasks: List<Task>, totalMs: Double): Timeline {
        scheduler.start(tasks)
        val runs = mutableListOf<Run>()
        var now = 0.0
        while (now < totalMs - 1e-9) {
            val task = scheduler.pick(tasks)
            val ms = minOf(scheduler.sliceFor(task), totalMs - now)
            task.ranMs += ms
            scheduler.charge(task, ms, tasks)
            runs += Run(task.name, now, ms)
            now += ms
        }
        return Timeline(runs, totalMs)
    }
}

/** The simplest fair policy: everyone gets the same slice, in turn. Nice is ignored. */
class RoundRobin(private val sliceMs: Double = 3.0) : Scheduler {
    private var next = 0

    override fun pick(tasks: List<Task>): Task = tasks[next++ % tasks.size]   // the next one in line, wrapping around

    override fun sliceFor(task: Task) = sliceMs

    override fun charge(task: Task, ms: Double, tasks: List<Task>) {}       // nothing to remember
}

/**
 * Weighted fair share, the idea behind CFS (Linux 2.6.23 to 6.5): always run the task whose
 * virtual runtime is smallest, and make virtual time pass more slowly for heavier tasks.
 */
class WeightedFair(private val sliceMs: Double = 3.0) : Scheduler {
    override fun pick(tasks: List<Task>): Task = tasks.minBy { it.vruntime }   // the one furthest behind; first wins ties

    override fun sliceFor(task: Task) = sliceMs                               // one fixed slice for everyone

    override fun charge(task: Task, ms: Double, tasks: List<Task>) {
        task.vruntime += ms * Nice.NICE_0 / task.weight                         // nice 10: 1 ms real = 9.3 ms virtual
    }
}

/**
 * Earliest Eligible Virtual Deadline First, Linux's fair scheduler since 6.6.
 * A task is eligible when it is owed CPU time: its vruntime is at or behind the weighted average.
 * Among eligible tasks, the one whose current slice has the earliest virtual deadline runs.
 */
class Eevdf : Scheduler {
    /** A slice of real time in virtual time: a light task's 3 ms slice ends far ahead on the virtual clock. Written for you. */
    fun virtualSlice(task: Task): Double = task.sliceMs * Nice.NICE_0 / task.weight

    /** Every task's first deadline is one virtual slice ahead. Written for you. */
    override fun start(tasks: List<Task>) {
        tasks.forEach { it.deadline = it.vruntime + virtualSlice(it) }
    }

    /** The weighted average vruntime, V: where every task would be if the CPU had been shared perfectly. Written for you. */
    fun average(tasks: List<Task>): Double = tasks.sumOf { it.weight * it.vruntime } / tasks.sumOf { it.weight }

    /** Owed CPU time: lag = weight * (V - vruntime) is zero or positive. */
    fun eligible(task: Task, tasks: List<Task>): Boolean = task.vruntime <= average(tasks) + 1e-9

    override fun pick(tasks: List<Task>): Task =
        tasks.filter { eligible(it, tasks) }.minBy { it.deadline }             // never empty: the smallest vruntime is <= V

    override fun sliceFor(task: Task) = task.sliceMs                           // each task's own request

    override fun charge(task: Task, ms: Double, tasks: List<Task>) {
        task.vruntime += ms * Nice.NICE_0 / task.weight
        if (task.vruntime >= task.deadline - 1e-9) {                           // slice used up: ask for the next one
            task.deadline = task.vruntime + virtualSlice(task)
        }
    }
}
