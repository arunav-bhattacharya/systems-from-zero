package sfz.stream.l04.demo

/**
 * Lesson stream-04, Try it 3: one-minute counts for merchant m-7 with a watermark. One on-time event
 * a second (event times 0 s to 299 s) and three stragglers that arrive after the stream has passed
 * the end of their window by 5 s, 30 s and 90 s. Run it with a grace period: -Pargs=10 (seconds).
 */

data class Ev(val eventTime: Long, val note: String = "")

fun stragglers(): List<Ev> = buildList {
    for (s in 0 until 300) {
        add(Ev(s * 1000L))
        when (s) {
            65 -> add(Ev(59_000, "late: 5 s past its window"))
            150 -> add(Ev(100_000, "late: 30 s past its window"))
            270 -> add(Ev(130_000, "late: 90 s past its window"))
        }
    }
}

fun main(args: Array<String>) {
    val grace = (args.firstOrNull()?.toLong() ?: 0) * 1000
    val size = 60_000L
    var watermark = Long.MIN_VALUE                      // stream time: the largest event time seen so far
    val open = sortedMapOf<Long, Int>()                 // window start -> count
    var dropped = 0
    println("1-minute windows, grace ${grace / 1000} s")
    for (e in stragglers()) {
        watermark = maxOf(watermark, e.eventTime)
        val start = e.eventTime - e.eventTime % size
        if (start + size + grace <= watermark) {
            dropped++
            println("  watermark %3d s: event at %3d s DROPPED, window %3d-%3d s already closed (${e.note})".format(watermark / 1000, e.eventTime / 1000, start / 1000, (start + size) / 1000))
            continue
        }
        if (e.note.isNotEmpty()) println("  watermark %3d s: event at %3d s counted, window %3d-%3d s still open (${e.note})".format(watermark / 1000, e.eventTime / 1000, start / 1000, (start + size) / 1000))
        open.merge(start, 1, Int::plus)
        while (open.isNotEmpty() && open.firstKey() + size + grace <= watermark) {
            val s = open.firstKey()
            println("  watermark %3d s: window %3d-%3d s is final, count = %d".format(watermark / 1000, s / 1000, (s + size) / 1000, open.remove(s)))
        }
    }
    println("  end of input: still open ${open.keys.map { "${it / 1000}-${(it + size) / 1000} s" }}")
    println("dropped as late: $dropped")
}
