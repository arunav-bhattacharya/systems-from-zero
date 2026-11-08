package sfz.stream.l04

/**
 * Lesson stream-04, exercise 3: count per key and per event-time window, the way a stream
 * processor does it. Events come one at a time, in the order they arrived, and a watermark decides
 * when a window is final.
 *
 * The watermark here is Kafka Streams' "stream time": the largest event time seen so far. A
 * window [start, end) stays open until the watermark reaches end + [graceMs]. Then its count is
 * final: it is emitted once, and an event that still belongs to it is dropped as late.
 *
 * Check it: ./gradlew :sim:test --tests 'sfz.stream.l04.*'   (from the labs folder)
 */
class WindowedCounter(val sizeMs: Long, val graceMs: Long) {

    /** One final count, and the watermark at the moment it was emitted. */
    data class Result(val key: String, val window: Window, val count: Int, val emittedAtWatermark: Long)

    /** The largest event time seen so far. Long.MIN_VALUE before the first event. */
    var watermark: Long = Long.MIN_VALUE
        private set

    /** How many events arrived for a window that had already closed. */
    var lateDropped: Int = 0
        private set

    /** Final counts, in the order the windows closed. */
    val results: MutableList<Result> = mutableListOf()

    /**
     * Exercise 3a. Process one event:
     * 1. move the watermark up to [Event.eventTime] if the event is newer;
     * 2. find its tumbling window ([Windows.tumbling]). If that window is closed (the watermark has
     *    reached its end + graceMs), count the event in [lateDropped] and stop;
     * 3. otherwise add one to the count for (key, window);
     * 4. close every open window whose end + graceMs is at or below the watermark: add a [Result]
     *    for each (earliest window first, then by key) and forget its count.
     */
    fun onEvent(e: Event) {
        TODO("exercise 3a: watermark, late check, count, close")
    }

    /**
     * Exercise 3b. The input has ended: close every window that is still open, earliest first, then
     * by key, with the current watermark in [Result.emittedAtWatermark].
     */
    fun flush() {
        TODO("exercise 3b: emit what is still open")
    }
}
