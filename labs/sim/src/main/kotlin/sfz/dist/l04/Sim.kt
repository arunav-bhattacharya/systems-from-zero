package sfz.dist.l04

import java.util.PriorityQueue

/**
 * Virtual time for lesson dist-04 (given). Nothing here sleeps. [runUntil] runs the scheduled events in time order
 * and moves [now] from one to the next, so ten simulated minutes take a few milliseconds and every run with the same
 * seed gives exactly the same answer. Times are milliseconds.
 *
 * Every event has the time it runs ([at]) and the time it was due. They differ only for a paused process: a step due
 * during the pause runs when the pause ends. Events at the same time run in the order they were due, then in the
 * order they were scheduled, so when a pause ends the process catches up oldest step first.
 */
class Sim {
    var now: Long = 0
        private set

    private class Event(val at: Long, val due: Long, val seq: Long, val action: () -> Unit)

    private var seq = 0L
    private val queue = PriorityQueue(compareBy<Event>({ it.at }, { it.due }, { it.seq }))

    /** Runs [action] at [time]. [due] is when it was meant to run (the same, unless a pause pushed it back). */
    fun at(time: Long, due: Long = time, action: () -> Unit) {
        require(time >= now) { "time $time is in the past (now $now)" }
        queue += Event(time, due, seq++, action)
    }

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
