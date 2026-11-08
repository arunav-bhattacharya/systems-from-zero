package sfz.stream.l04.demo

/**
 * Lesson stream-04, Try it 1: a fraud dashboard counts card authorizations per second for one
 * merchant. 100 a second arrive, steadily. The counting consumer is redeployed: it stops at 60 s and
 * starts again at 120 s, then drains Kafka's backlog at 2,000 a second. Count the same events by
 * processing time and by event time.
 */

/** (event time, processing time) in ms for every event, in the order the consumer read them. */
fun redeploy(perSecond: Int = 100, seconds: Int = 180, stopAt: Long = 60_000, restartAt: Long = 120_000, drainPerSecond: Int = 2_000): List<Pair<Long, Long>> {
    val spacingUs = 1_000_000L / drainPerSecond
    var freeAtUs = 0L
    return (0 until perSecond * seconds).map { i ->
        val eventTime = i * 1000L / perSecond
        var readyUs = (eventTime + 5) * 1000                                  // 5 ms from the card terminal to the consumer
        if (readyUs >= stopAt * 1000 && readyUs < restartAt * 1000) readyUs = restartAt * 1000   // waits in Kafka
        val startUs = maxOf(readyUs, freeAtUs)
        freeAtUs = startUs + spacingUs
        eventTime to startUs / 1000
    }
}

fun main() {
    val events = redeploy()
    val byProcessing = events.groupingBy { it.second / 1000 }.eachCount()
    val byEvent = events.groupingBy { it.first / 1000 }.eachCount()
    println("second | by processing time | by event time")
    for (s in listOf(58L, 59, 60, 61, 119, 120, 121, 122, 123, 124, 125)) {
        println("%6d | %18d | %13d".format(s, byProcessing[s] ?: 0, byEvent[s] ?: 0))
    }
    println("max per second: by processing time ${byProcessing.values.max()}, by event time ${byEvent.values.max()}")
    println("seconds with zero by processing time: ${(0L until 180).count { byProcessing[it] == null }}")
}
