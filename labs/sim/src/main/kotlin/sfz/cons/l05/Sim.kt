package sfz.cons.l05

import java.util.PriorityQueue
import kotlin.random.Random

/**
 * Virtual time for lesson cons-05 (given). Nothing here sleeps or starts a thread: [runUntil] takes the
 * scheduled events in time order and moves [now] from one to the next, so a simulated minute takes a
 * millisecond and the same seed always gives the same run. Times are milliseconds. Two events at the
 * same millisecond run in the order they were scheduled.
 */
class Sim(seed: Long = 1) {
    val random = Random(seed)

    var now: Long = 0
        private set

    private class Event(val at: Long, val seq: Long, val action: () -> Unit)

    private var seq = 0L
    private val queue = PriorityQueue(compareBy<Event>({ it.at }, { it.seq }))

    /** Runs [action] at [time]. */
    fun at(time: Long, action: () -> Unit) {
        require(time >= now) { "time $time is in the past (now $now)" }
        queue += Event(time, seq++, action)
    }

    /** Runs [action] [delayMs] from now. */
    fun after(delayMs: Long, action: () -> Unit) = at(now + delayMs, action)

    /** Runs every event scheduled at or before [time], then sets the clock to [time]. */
    fun runUntil(time: Long) {
        while (queue.isNotEmpty() && queue.peek().at <= time) {
            val e = queue.poll()
            now = e.at
            e.action()
        }
        if (time > now) now = time
    }
}
