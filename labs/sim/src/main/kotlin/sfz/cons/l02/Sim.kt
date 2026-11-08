package sfz.cons.l02

import java.util.PriorityQueue
import kotlin.random.Random

/**
 * Virtual time for lesson cons-02 (given). Nothing sleeps: [run] takes the scheduled events in time
 * order and moves [now] from one to the next. All randomness comes from [random], seeded, so a seed
 * replays exactly the same run. Two events at the same millisecond run in the order they were added.
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

    /** Runs events until none are left or the clock passes [untilMs]. */
    fun run(untilMs: Long = Long.MAX_VALUE) {
        while (queue.isNotEmpty() && queue.peek().at <= untilMs) {
            val e = queue.poll()
            now = e.at
            e.action()
        }
    }
}

/**
 * A network that delivers every message, after a random delay. Most messages take [minMs] to [maxMs];
 * a fraction [slowChance] of them hit a slow path and take up to [slowMaxMs] (a long tail, as on real
 * networks). Messages can overtake each other. [sent] counts messages, for comparing protocols.
 */
class Network(
    private val sim: Sim,
    private val minMs: Long = 1,
    private val maxMs: Long = 10,
    private val slowChance: Double = 0.1,
    private val slowMaxMs: Long = 100,
) {
    var sent = 0L
        private set

    fun send(deliver: () -> Unit) {
        sent++
        val r = sim.random
        val delay = if (r.nextDouble() < slowChance) r.nextLong(maxMs, slowMaxMs + 1) else r.nextLong(minMs, maxMs + 1)
        sim.after(delay, deliver)
    }
}
