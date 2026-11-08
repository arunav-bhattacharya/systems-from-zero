package sfz.found.l02

import java.util.PriorityQueue
import kotlin.random.Random

/**
 * A server with one worker that handles requests in the order they arrive, in virtual time
 * (microseconds as Long, no real waiting). Most requests need 300 to 600 µs of work; one in twenty
 * takes a slow path of 2 to 5 ms. Between [pauseAt] and [pauseAt] + [pauseMicros] the whole
 * process is frozen, like a long garbage-collection pause: nothing is served, and work that was
 * in progress waits too.
 *
 * Call [submit] in order of arrival time (never earlier than the previous call).
 */
class PausingServer(val pauseAt: Long = Long.MAX_VALUE, val pauseMicros: Long = 0, seed: Long = 1) {
    private val rnd = Random(seed)
    private var freeAt = 0L
    private var lastArrival = 0L
    private val pauseEnd = if (pauseAt == Long.MAX_VALUE) Long.MAX_VALUE else pauseAt + pauseMicros

    /** Takes a request that arrives at [arrival] and returns the time its answer is ready. */
    fun submit(arrival: Long): Long {
        require(arrival >= lastArrival) { "submit requests in arrival order" }
        lastArrival = arrival
        val service = if (rnd.nextInt(20) == 0) rnd.nextLong(2_000, 5_000) else rnd.nextLong(300, 600)
        var start = maxOf(arrival, freeAt)                       // wait for the worker
        if (start in pauseAt until pauseEnd) start = pauseEnd   // frozen: wait for the pause to end
        var finish = start + service
        if (start < pauseAt && finish > pauseAt) finish += pauseMicros   // the pause hit mid-request
        freeAt = finish
        return finish
    }
}

/** What a closed-loop run measured, two ways. */
class ClosedLoopResult(
    /** Latency from the moment each request was really sent: what a naive load tool reports. */
    val fromActualSend: LogHistogram,
    /** Latency from the moment each request should have been sent, by the plan. */
    val fromPlannedSend: LogHistogram,
)

/**
 * The closed model (finished): [connections] connections. Each one sends a request, waits for the
 * answer, and only then sends its next request: at its next planned slot, or straight away if it
 * is already late. Together they aim at [ratePerSec]. While the server is frozen, every connection
 * is stuck waiting, so the requests that should have gone out during the pause are sent late, and
 * timed from when they were finally sent.
 */
fun closedLoop(server: PausingServer, ratePerSec: Int, connections: Int, durationMicros: Long): ClosedLoopResult {
    val actual = LogHistogram()
    val planned = LogHistogram()
    val interval = 1_000_000L * connections / ratePerSec        // per connection
    // (time the connection sends next, planned time of that request, connection id)
    val ready = PriorityQueue<Triple<Long, Long, Int>>(compareBy({ it.first }, { it.third }))
    for (c in 0 until connections) {
        val first = c * interval / connections                   // spread the connections out
        ready += Triple(first, first, c)
    }
    while (ready.isNotEmpty()) {
        val (sendAt, plannedAt, c) = ready.poll()
        if (plannedAt >= durationMicros) continue                 // this connection is done
        val done = server.submit(sendAt)
        actual.record(done - sendAt)
        planned.record(done - plannedAt)
        val nextPlanned = plannedAt + interval
        ready += Triple(maxOf(nextPlanned, done), nextPlanned, c) // can't send before the answer is back
    }
    return ClosedLoopResult(actual, planned)
}

/**
 * The open model: requests arrive at a fixed rate whatever the server is doing, the way real
 * users do. Request i is sent at i * 1,000,000 / [ratePerSec] µs, for every i whose send time is
 * before [durationMicros]. Submit each one to the server, and record (answer time - send time).
 * Returns the histogram.
 */
fun openLoop(server: PausingServer, ratePerSec: Int, durationMicros: Long): LogHistogram {
    val h = LogHistogram()
    var i = 0L
    while (true) {
        val sendAt = i * 1_000_000L / ratePerSec               // the schedule never waits for an answer
        if (sendAt >= durationMicros) break
        h.record(server.submit(sendAt) - sendAt)
        i++
    }
    return h
}
