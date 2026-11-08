package sfz.repl.l01

import java.util.PriorityQueue

/**
 * Virtual time for lesson repl-01 (given). Nothing here sleeps. [runUntil] runs the scheduled events
 * in time order and moves [now] from one to the next, so a simulated second takes microseconds and
 * every run gives exactly the same answer. Times are milliseconds.
 *
 * Two events at the same millisecond run in the order they were scheduled.
 */
class Sim {
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
            val event = queue.poll()
            now = event.at
            event.action()
        }
        if (time > now) now = time
    }
}
