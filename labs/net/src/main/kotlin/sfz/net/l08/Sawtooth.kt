package sfz.net.l08

import kotlin.math.cbrt
import kotlin.math.pow

/**
 * Runs [reno] for [rounds] round trips over a path that can hold [capacity] segments in flight
 * (the bandwidth-delay product plus the bottleneck router's queue), and returns the window at the
 * start of each round: the sawtooth.
 *
 * Each round, the sender sends `w = cwnd` segments.
 * - If `w > capacity`, the router's queue overflows and a segment is dropped. The sender sees
 *   three duplicate ACKs: call [Reno.onTripleDuplicateAck] once, and nothing else that round.
 * - Otherwise every segment arrives: call [Reno.onAck] once per segment, `w` times.
 */
fun sawtooth(reno: Reno, rounds: Int, capacity: Int): List<Int> {
    TODO("record cwnd; lose one segment when cwnd > capacity, else one onAck() per segment sent")
}

/**
 * CUBIC's window [t] seconds after its last loss (RFC 9438, the default on Linux):
 * `W(t) = c * (t - k)^3 + wMax`, where `k = cbrt(wMax * (1 - beta) / c)`.
 *
 * [wMax] is the window when the loss happened. Right after the loss the window is `beta * wMax`;
 * it climbs quickly at first, flattens out near [wMax] (at `t = k`), then speeds up again to
 * probe for more. Time is in seconds, not round trips, so the curve is the same on a 1 ms path and
 * a 100 ms one.
 */
fun cubicWindow(t: Double, wMax: Double, c: Double = 0.4, beta: Double = 0.7): Double {
    TODO("c * (t - k)^3 + wMax with k = cbrt(wMax * (1 - beta) / c)")
}
