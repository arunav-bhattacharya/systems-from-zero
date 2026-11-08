package sfz.found.l02.demo

import java.util.PriorityQueue
import kotlin.math.ceil
import kotlin.random.Random

/**
 * The lying load test, in virtual time. A one-worker server answers in about half a millisecond,
 * and (in the second run) freezes for 1.4 s, ten seconds in. Two load generators aim at 1,000
 * requests a second for 30 s: a closed one with 10 connections, and an open one.
 */
private class Server(val pauseAt: Long, val pauseMicros: Long) {
    private val rnd = Random(1)
    private var freeAt = 0L
    fun submit(arrival: Long): Long {
        val service = if (rnd.nextInt(20) == 0) rnd.nextLong(2_000, 5_000) else rnd.nextLong(300, 600)
        var start = maxOf(arrival, freeAt)
        if (start >= pauseAt && start < pauseAt + pauseMicros) start = pauseAt + pauseMicros
        var finish = start + service
        if (start < pauseAt && finish > pauseAt) finish += pauseMicros
        freeAt = finish
        return finish
    }
}

private const val RATE = 1_000
private const val DURATION = 30_000_000L

/** Returns (latency from the actual send, latency from the planned send) for every request. */
private fun closed(server: Server, connections: Int): Pair<LongArray, LongArray> {
    val actual = ArrayList<Long>()
    val planned = ArrayList<Long>()
    val interval = 1_000_000L * connections / RATE
    val ready = PriorityQueue<Triple<Long, Long, Int>>(compareBy({ it.first }, { it.third }))
    for (c in 0 until connections) (c * interval / connections).let { ready += Triple(it, it, c) }
    while (ready.isNotEmpty()) {
        val (sendAt, plannedAt, c) = ready.poll()
        if (plannedAt >= DURATION) continue
        val done = server.submit(sendAt)
        actual += done - sendAt
        planned += done - plannedAt
        ready += Triple(maxOf(plannedAt + interval, done), plannedAt + interval, c)
    }
    return actual.toLongArray() to planned.toLongArray()
}

private fun open(server: Server): LongArray =
    LongArray((DURATION * RATE / 1_000_000).toInt()) { i -> (i * 1_000_000L / RATE).let { server.submit(it) - it } }

private fun ms(us: Long) = if (us >= 100_000) "%.2f s".format(us / 1e6) else "%.2f ms".format(us / 1e3)

private fun row(name: String, lat: LongArray) {
    val s = lat.sortedArray()
    fun q(p: Double) = s[maxOf(1, ceil(p * s.size).toInt()) - 1]
    println("%-28s %7d %10s %10s %10s %10s %10s".format(name, s.size, ms(q(0.5)), ms(q(0.9)), ms(q(0.99)), ms(q(0.999)), ms(s.last())))
}

fun main() {
    for ((title, pause) in listOf("quiet server" to 0L, "server frozen for 1.4 s at t=10 s" to 1_400_000L)) {
        println("-- $title")
        println("%-28s %7s %10s %10s %10s %10s %10s".format("", "count", "p50", "p90", "p99", "p99.9", "max"))
        val (actual, planned) = closed(Server(10_000_000L, pause), connections = 10)
        row("closed, timed from send", actual)
        row("closed, timed from plan", planned)
        row("open, fixed arrival rate", open(Server(10_000_000L, pause)))
    }
}
