package sfz.dist.l03

import java.util.PriorityQueue
import kotlin.random.Random

/**
 * Virtual time for lesson dist-03 (given). Nothing here sleeps or starts a thread. [run] takes the
 * scheduled events in time order and moves [now] from one to the next, so a simulated hour takes a
 * few milliseconds and the same seed always gives the same run.
 *
 * [now] is the true time, in epoch milliseconds: what a perfect clock would read. It starts at
 * [START], 10:00:00.000 UTC on 7 November 2026. No node can read it; nodes read their own
 * [DriftingClock]s.
 *
 * Every random choice in a simulation comes from [random], which is seeded once. Two events at the
 * same millisecond run in the order they were scheduled.
 */
class Sim(seed: Long = 1) {
    companion object {
        /** 2026-11-07T10:00:00Z */
        const val START = 1_794_045_600_000L
    }

    val random = Random(seed)

    var now: Long = START
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
        while (queue.isNotEmpty() && queue.peek().at <= time) step()
        if (time > now) now = time
    }

    /** Runs events until none are left. */
    fun run() {
        while (queue.isNotEmpty()) step()
    }

    private fun step() {
        val event = queue.poll()
        now = event.at
        event.action()
    }
}
