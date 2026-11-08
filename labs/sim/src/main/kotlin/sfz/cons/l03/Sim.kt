package sfz.cons.l03

import java.util.PriorityQueue
import kotlin.random.Random

/**
 * Virtual time for lesson cons-03 (given). Nothing sleeps: [run] takes the scheduled events in time
 * order and moves [now] from one to the next. All randomness comes from [random], seeded, so one
 * seed replays exactly the same run. Two events at the same millisecond run in the order added.
 */
class Sim(seed: Long) {
    val random = Random(seed)
    var now: Long = 0
        private set

    private class Event(val at: Long, val seq: Long, val action: () -> Unit)

    private var seq = 0L
    private val queue = PriorityQueue(compareBy<Event>({ it.at }, { it.seq }))

    fun after(delayMs: Long, action: () -> Unit) {
        queue += Event(now + delayMs, seq++, action)
    }

    /** Runs events until none are left, [stop] says so, or the clock passes [untilMs]. */
    fun run(untilMs: Long = Long.MAX_VALUE, stop: () -> Boolean = { false }) {
        while (queue.isNotEmpty() && queue.peek().at <= untilMs && !stop()) {
            val e = queue.poll()
            now = e.at
            e.action()
        }
    }
}

/**
 * An unreliable network (given). Each message is lost with probability [dropRate], delivered twice
 * with probability [duplicateRate], and otherwise arrives after [minMs] to [maxMs]. Messages overtake
 * each other freely. [sent] counts messages handed to the network.
 */
class Network(
    private val sim: Sim,
    private val minMs: Long = 1,
    private val maxMs: Long = 10,
    private val dropRate: Double = 0.0,
    private val duplicateRate: Double = 0.0,
) {
    var sent = 0L
        private set

    fun send(deliver: () -> Unit) {
        sent++
        val r = sim.random
        if (r.nextDouble() < dropRate) return
        sim.after(r.nextLong(minMs, maxMs + 1), deliver)
        if (r.nextDouble() < duplicateRate) sim.after(r.nextLong(minMs, maxMs + 1), deliver)
    }
}
