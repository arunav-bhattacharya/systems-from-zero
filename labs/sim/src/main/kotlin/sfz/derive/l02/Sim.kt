package sfz.derive.l02

import java.util.PriorityQueue
import kotlin.random.Random

/**
 * Virtual time for lesson derive-02 (given). Nothing here sleeps or starts a thread: [runUntil]
 * takes scheduled actions in time order and moves [now] from one to the next, so a simulated
 * minute takes a few milliseconds and the same seed always gives the same run. Times are in
 * milliseconds. Two actions at the same millisecond run in the order they were scheduled.
 */
class Sim(seed: Long = 1) {
    val random = Random(seed)

    var now: Long = 0
        private set

    private class Action(val at: Long, val seq: Long, val run: () -> Unit)

    private var seq = 0L
    private val queue = PriorityQueue(compareBy<Action>({ it.at }, { it.seq }))

    /** Runs [action] at [time]. */
    fun at(time: Long, action: () -> Unit) {
        require(time >= now) { "time $time is in the past (now $now)" }
        queue += Action(time, seq++, action)
    }

    /** Runs [action] [delayMs] from now. */
    fun after(delayMs: Long, action: () -> Unit) = at(now + delayMs, action)

    /** Runs every action scheduled at or before [time], then sets the clock to [time]. */
    fun runUntil(time: Long) {
        while (queue.isNotEmpty() && queue.peek().at <= time) {
            val a = queue.poll()
            now = a.at
            a.run()
        }
        if (time > now) now = time
    }
}
