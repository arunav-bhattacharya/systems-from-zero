package sfz.bigdata.l11

import java.time.Duration
import java.time.Instant
import java.util.TreeMap

data class Window(val start: Instant, val end: Instant)

data class WindowCount(val window: Window, val count: Long)

class WindowedCounter(val size: Duration, val delay: Duration) {

    var watermark: Instant = Instant.EPOCH
        private set

    var dropped: Long = 0
        private set

    // the state store: one count per open window, keyed by window start
    private val state = TreeMap<Instant, Long>()
    private var maxEventTime: Instant? = null

    fun windowOf(t: Instant): Window {
        val ms = size.toMillis()
        // floorMod keeps times before the epoch in the right window too
        val start = Instant.ofEpochMilli(t.toEpochMilli() - Math.floorMod(t.toEpochMilli(), ms))
        return Window(start, start.plus(size))
    }

    fun open(): List<WindowCount> = state.map { (start, n) -> WindowCount(Window(start, start.plus(size)), n) }

    fun batch(events: List<Instant>): List<WindowCount> {
        // 1. the late-event filter uses the watermark from BEFORE this batch, and it tests the
        //    window's end, not the event time: an event older than the delay still counts while
        //    its window is open
        for (t in events) {
            val w = windowOf(t)
            if (!w.end.isAfter(watermark)) dropped++ else state.merge(w.start, 1L, Long::plus)
        }
        // 2. the watermark follows the latest event time ever seen, minus the allowed delay, and only moves forward
        events.maxOrNull()?.let { m -> if (maxEventTime == null || m.isAfter(maxEventTime)) maxEventTime = m }
        maxEventTime?.minus(delay)?.let { if (it.isAfter(watermark)) watermark = it }
        // 3. a window is final once the watermark reaches its end: emit it once and drop its state
        val closed = state.headMap(watermark.minus(size), true).toMap()
        closed.keys.forEach(state::remove)
        return closed.map { (start, n) -> WindowCount(Window(start, start.plus(size)), n) }
    }
}
