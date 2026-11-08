package sfz.stream.l04.demo

/**
 * Lesson stream-04, Try it 2: four card authorizations by one customer, and the windows each kind
 * of window puts them in. Times are hh:mm:ss on one day.
 */

fun hms(ms: Long) = "%02d:%02d:%02d".format(ms / 3_600_000, ms / 60_000 % 60, ms / 1000 % 60)
fun at(h: Int, m: Int, s: Int) = (h * 3600L + m * 60L + s) * 1000
fun span(start: Long, end: Long) = "[${hms(start)}, ${hms(end)})"

fun main() {
    val minute = 60_000L
    val times = listOf(at(9, 10, 30), at(9, 14, 20), at(9, 16, 10), at(9, 52, 0))

    println("tumbling, 5 minutes (aligned to 00:00:00, start included, end excluded):")
    for (t in times) { val s = t - t % (5 * minute); println("  ${hms(t)} -> ${span(s, s + 5 * minute)}") }

    println("hopping, 5 minutes, advancing by 1 minute (Flink and Beam call this sliding):")
    val t = times[1]
    val windows = generateSequence(t - t % minute) { it - minute }.takeWhile { it + 5 * minute > t }.toList().reversed()
    println("  ${hms(t)} is in ${windows.size} windows: ${windows.joinToString(" ") { span(it, it + 5 * minute) }}")

    println("sliding, 5 minutes (Kafka Streams: one window per record, both ends included):")
    for (end in times) {
        val inside = times.filter { it in (end - 5 * minute)..end }
        println("  [${hms(end - 5 * minute)}, ${hms(end)}]  holds ${inside.size}: ${inside.joinToString { hms(it) }}")
    }

    println("session, 30-minute inactivity gap:")
    val sessions = mutableListOf(mutableListOf(times[0]))
    for (x in times.drop(1)) if (x - sessions.last().last() <= 30 * minute) sessions.last() += x else sessions += mutableListOf(x)
    sessions.forEach { println("  ${hms(it.first())} to ${hms(it.last())}: ${it.size} event${if (it.size == 1) "" else "s"}") }
}
