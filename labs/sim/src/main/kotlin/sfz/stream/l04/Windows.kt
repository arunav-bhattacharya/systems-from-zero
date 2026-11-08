package sfz.stream.l04

/**
 * Lesson stream-04, exercises 1 and 2: which windows an event belongs to.
 *
 * Check it: ./gradlew :sim:test --tests 'sfz.stream.l04.*'   (from the labs folder)
 */
object Windows {

    /**
     * Exercise 1a. The one tumbling window of [sizeMs] that holds time [t]. Windows are aligned to
     * time 0, as in Kafka Streams and Flink: they start at 0, sizeMs, 2 * sizeMs... and include their
     * start but not their end. With 60 s windows, t = 59,999 is in [0, 60 s) and t = 60,000 in
     * [60 s, 120 s). Times are never negative here.
     */
    fun tumbling(t: Long, sizeMs: Long): Window {
        TODO("exercise 1a: round t down to a multiple of sizeMs")
    }

    /**
     * Exercise 1b. Every hopping window that holds [t], earliest first. Hopping windows have size
     * [sizeMs] and start every [advanceMs] (at 0, advanceMs, 2 * advanceMs...), so they overlap and t
     * is in about sizeMs / advanceMs of them. Kafka Streams calls these hopping windows; Flink and
     * Beam call the same thing sliding windows. A window that would start before 0 doesn't exist.
     */
    fun hopping(t: Long, sizeMs: Long, advanceMs: Long): List<Window> {
        TODO("exercise 1b: the windows starting at multiples of advanceMs that contain t")
    }

    /** One session of one key: its first and last event time and how many events it holds. */
    data class Session(val first: Long, val last: Long, val count: Int)

    /**
     * Exercise 2. Splits one key's event [times] (in any order: late events arrive out of order)
     * into sessions. A session goes on while the gap between one event and the next is at most
     * [gapMs]; a longer silence ends it. Return the sessions earliest first. A late event that falls
     * in a gap can join two sessions into one: that's why session windows merge.
     */
    fun sessions(times: List<Long>, gapMs: Long): List<Session> {
        TODO("exercise 2: sort, then cut wherever the gap is more than gapMs")
    }
}
