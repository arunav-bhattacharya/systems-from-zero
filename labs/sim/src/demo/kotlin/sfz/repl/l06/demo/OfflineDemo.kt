package sfz.repl.l06.demo

/**
 * A dispute agent works through six clicks on a laptop on a train. The server is a 150 ms round
 * trip away, and the network is gone from t=2,000 ms to t=12,000 ms.
 *
 * Design 1 sends every click to the server and waits (a 5-second timeout).
 * Design 2 writes to a local replica, shows the change in the next frame (16 ms at 60 Hz),
 * and a sync engine uploads queued changes whenever the network is up.
 */
private const val RTT = 150L
private const val FRAME = 16L
private const val TIMEOUT = 5_000L
private val offline = 2_000L until 12_000L

private val clicks = listOf(
    0L to "open dispute DSP-311",
    800L to "set reason: not received",
    2_500L to "attach courier receipt",
    4_000L to "add note: customer called",
    9_000L to "set status: under review",
    13_000L to "assign to team chargebacks",
)

fun main() {
    println("-- design 1: every click waits for the server --")
    for ((at, what) in clicks) {
        val result = if (at in offline) "spinner for ${TIMEOUT / 1000} s, then a network error: retype it later" else "on screen after $RTT ms"
        println("t=%,6d  %-28s %s".format(at, what, result))
    }

    println()
    println("-- design 2: local replica plus a sync engine --")
    val queue = ArrayDeque<String>()
    for ((at, what) in clicks) {
        queue += what
        val synced = if (at in offline) "queued (${queue.size} waiting)" else "synced at t=%,d".format(at + RTT).also { queue.clear() }
        println("t=%,6d  %-28s on screen after %d ms, %s".format(at, what, FRAME, synced))
        if (at in offline && clicks.none { it.first > at && it.first in offline }) {
            println("t=%,6d  network back: %d queued changes uploaded, confirmed at t=%,d".format(offline.last + 1, queue.size, offline.last + 1 + RTT))
            queue.clear()
        }
    }
}
