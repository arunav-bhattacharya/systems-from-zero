package sfz.bigdata.l11

import java.time.Duration
import java.time.Instant

/** A tumbling event-time window: it holds the events with `start <= event time < end`. */
data class Window(val start: Instant, val end: Instant)

/** A window and the number of events counted in it. */
data class WindowCount(val window: Window, val count: Long)

/**
 * A model of what Spark Structured Streaming does for
 * `withWatermark("event_time", delay).groupBy(window(col("event_time"), size)).count()`
 * in append mode, one micro-batch at a time. Build it, and the tests check it against Spark.
 *
 * Spark emits finished windows in an extra micro-batch with no data, right after the batch that
 * moved the watermark; this model folds that into the same [batch] call.
 */
class WindowedCounter(val size: Duration, val delay: Duration) {

    /** The current watermark. No window that ends at or before it can change any more. Starts at the epoch. */
    var watermark: Instant = Instant.EPOCH
        private set

    /** Events dropped so far because their window had already closed. */
    var dropped: Long = 0
        private set

    /**
     * The window [t] falls in. Windows start at whole multiples of [size] counted from the epoch,
     * so with 5-minute windows 10:03 falls in [10:00, 10:05) and 10:05 in [10:05, 10:10).
     */
    fun windowOf(t: Instant): Window {
        TODO("floor the epoch millis of t to a multiple of size")
    }

    /** The windows still open (held in state), with their counts so far, sorted by start. */
    fun open(): List<WindowCount> {
        TODO("the windows you are still counting")
    }

    /**
     * Runs one micro-batch of [events] (event times, in any order):
     * 1. Using the watermark as it was before this batch, drop every event whose window ends at
     *    or before the watermark (count it in [dropped]); count every other event in its window.
     * 2. Move the watermark to (the latest event time seen in any batch so far) minus [delay],
     *    unless that is earlier than the current watermark: it never moves back.
     * 3. Emit and forget every open window that ends at or before the new watermark.
     *
     * Returns the emitted windows sorted by start: what append mode writes after this batch.
     */
    fun batch(events: List<Instant>): List<WindowCount> {
        TODO("drop late events, count the rest, advance the watermark, emit the closed windows")
    }
}
