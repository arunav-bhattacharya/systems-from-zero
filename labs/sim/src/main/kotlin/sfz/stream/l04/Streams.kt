package sfz.stream.l04

import kotlin.random.Random

/**
 * Lesson stream-04: everything in this file is given. Your exercises are in Windows.kt and
 * WindowedCounter.kt.
 *
 * Time is virtual: every timestamp is a number of milliseconds that the scenarios below compute, so
 * every count, every drop and every spike is exact and the same on every run.
 */

/**
 * One event: a card authorization at merchant [key]. [eventTime] is when the card was used (the
 * payment service stamped it); [processingTime] is when the stream processor read it.
 */
data class Event(val key: String, val eventTime: Long, val processingTime: Long)

/** A time window: [start] included, [end] excluded, both in ms. */
data class Window(val start: Long, val end: Long) {
    operator fun contains(t: Long): Boolean = t >= start && t < end
    override fun toString(): String = "[${start / 1000.0}s, ${end / 1000.0}s)"
}

object Scenario {

    /**
     * The redeploy. Merchant m-7 takes [perSecond] authorizations a second, evenly spaced, for
     * [seconds] seconds; each reaches the processor 5 ms after it happened. The processor stops at
     * [stopAt] and starts again at [restartAt] (a deploy). Kafka keeps what arrives meanwhile, and on
     * restart the processor drains the backlog at [drainPerSecond]. Returns the events in the order
     * the processor read them.
     */
    fun redeploy(
        perSecond: Int = 100,
        seconds: Int = 180,
        stopAt: Long = 60_000,
        restartAt: Long = 120_000,
        drainPerSecond: Int = 2_000,
    ): List<Event> {
        val spacingUs = 1_000_000L / drainPerSecond          // the processor's fastest pace, in microseconds
        var freeAtUs = 0L                                    // when the processor can take the next event
        return (0 until perSecond * seconds).map { i ->
            val eventTime = i * 1000L / perSecond
            var readyUs = (eventTime + 5) * 1000
            if (readyUs >= stopAt * 1000 && readyUs < restartAt * 1000) readyUs = restartAt * 1000   // waits in Kafka
            val startUs = maxOf(readyUs, freeAtUs)
            freeAtUs = startUs + spacingUs
            Event("m-7", eventTime, startUs / 1000)
        }
    }

    /**
     * Out-of-order arrival. [perSecond] events a second for [seconds] seconds, spread over
     * [keys] merchants; each one's trip to the processor takes between 0 and [maxDelayMs] ms (seeded
     * by [seed]), so a later event often arrives first. Returns the events in arrival order.
     */
    fun jittered(seed: Long, perSecond: Int = 100, seconds: Int = 60, maxDelayMs: Long = 2_000, keys: Int = 3): List<Event> {
        val random = Random(seed)
        return (0 until perSecond * seconds)
            .map { i ->
                val eventTime = i * 1000L / perSecond
                Event("m-${i % keys}", eventTime, eventTime + random.nextLong(0, maxDelayMs + 1))
            }
            .sortedWith(compareBy<Event>({ it.processingTime }, { it.eventTime }))
    }

    /**
     * Three stragglers. Merchant m-7 has one on-time event every second, event times 0 s to 299 s,
     * read as they happen. Three late events come in among them; the stream has already moved past
     * the end of their 1-minute window by 5 s, 30 s and 90 s:
     *
     *   event time  59 s (window 0-60 s)     read right after the on-time event of  65 s
     *   event time 100 s (window 60-120 s)   read right after the on-time event of 150 s
     *   event time 130 s (window 120-180 s)  read right after the on-time event of 270 s
     */
    fun stragglers(): List<Event> = buildList {
        for (s in 0 until 300) {
            add(Event("m-7", s * 1000L, s * 1000L))
            when (s) {
                65 -> add(Event("m-7", 59_000, 65_000))
                150 -> add(Event("m-7", 100_000, 150_000))
                270 -> add(Event("m-7", 130_000, 270_000))
            }
        }
    }
}

/** Counts [events] per tumbling window of [sizeMs], placing each by the clock you pass: event time or processing time. */
fun countPerWindow(events: List<Event>, sizeMs: Long, clock: (Event) -> Long): Map<Window, Int> =
    events.groupingBy { Windows.tumbling(clock(it), sizeMs) }.eachCount().toSortedMap(compareBy { it.start })
