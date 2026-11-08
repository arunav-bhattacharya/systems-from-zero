package sfz.batch.l13.demo

/**
 * One stage of 200 tasks on 20 task slots, on virtual time, run four ways. In the first case one
 * machine (two slots) has a failing disk and runs 30 times slower. In the second, one task has 30
 * times the data of the others (a skewed key). Each case runs without and with speculation, using
 * Spark's rule: once 90% of the stage's tasks are done, a task running longer than 3 times the
 * median task time gets a copy on a free slot, and whichever copy finishes first wins.
 */
fun main() {
    println("%-34s %18s %18s".format("stage of 200 tasks, 20 slots", "no speculation", "speculation"))
    for ((name, slowSlots, bigTask) in listOf(
        Triple("one slow machine (2 slots, 30x)", setOf(0, 1), -1),
        Triple("one skewed task (30x the data)", emptySet(), 137),
    )) {
        val plain = stage(slowSlots, bigTask, speculate = false)
        val spec = stage(slowSlots, bigTask, speculate = true)
        println("%-34s %15.1f s %15.1f s   (%d speculative %s)".format(name, plain.first, spec.first, spec.second, if (spec.second == 1) "copy" else "copies"))
    }
    println("a healthy stage takes %.1f s".format(stage(emptySet(), -1, speculate = false).first))
}

/** Returns the stage's finish time in seconds and the number of speculative copies launched. */
private fun stage(slowSlots: Set<Int>, bigTask: Int, speculate: Boolean): Pair<Double, Int> {
    val tasks = 200
    val slots = 20
    val work = DoubleArray(tasks) { if (it == bigTask) 30.0 * 4 else 4.0 }       // seconds on a healthy slot
    val speed = DoubleArray(slots) { if (it in slowSlots) 1.0 / 30 else 1.0 }
    data class Copy(val task: Int, val slot: Int, val start: Double)
    val running = mutableListOf<Copy>()
    val done = BooleanArray(tasks)
    val durations = mutableListOf<Double>()
    val busy = BooleanArray(slots)
    var next = 0
    var copies = 0
    var t = 0.0
    val dt = 0.1
    while (done.any { !it }) {
        // start pending tasks on free slots, lowest slot first
        for (s in 0 until slots) if (!busy[s] && next < tasks) { running += Copy(next++, s, t); busy[s] = true }
        // speculation check, as Spark does every 100 ms
        if (speculate && next == tasks && done.count { it } >= 0.9 * tasks) {
            val median = durations.sorted()[durations.size / 2]
            for (c in running.toList()) {
                val alreadyCopied = running.count { it.task == c.task } > 1
                if (!alreadyCopied && t - c.start > 3 * median) {
                    val free = (0 until slots).firstOrNull { !busy[it] } ?: continue
                    running += Copy(c.task, free, t); busy[free] = true; copies++
                }
            }
        }
        t += dt
        // finish copies whose work is done; the first copy of a task to finish wins, the other is killed
        for (c in running.toList()) {
            if (c !in running) continue
            if ((t - c.start) * speed[c.slot] >= work[c.task] - 1e-9) {
                done[c.task] = true
                durations += t - c.start
                for (o in running.filter { it.task == c.task }) { running.remove(o); busy[o.slot] = false }
            }
        }
    }
    return t to copies
}
