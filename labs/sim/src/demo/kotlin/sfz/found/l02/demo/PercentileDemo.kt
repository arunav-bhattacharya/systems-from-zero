package sfz.found.l02.demo

import kotlin.math.ceil
import kotlin.random.Random

/**
 * Ten pods behind one load balancer. Nine are healthy. One shares a host with a noisy neighbour,
 * and 15% of its requests take 900 ms. What is the service's p99?
 */
private fun quantile(sorted: LongArray, q: Double): Long = sorted[maxOf(1, ceil(q * sorted.size).toInt()) - 1]

fun main() {
    val rnd = Random(4)
    val pods = List(10) { pod ->
        LongArray(10_000) {
            val slow = pod == 9 && rnd.nextInt(100) < 15
            if (slow) 900L else rnd.nextLong(12, 26)      // milliseconds
        }.also { it.sort() }
    }

    println("pod   requests   mean    p50    p99")
    pods.forEachIndexed { i, p ->
        println("%3d   %8d   %4.0f   %4d   %4d".format(i, p.size, p.average(), quantile(p, 0.5), quantile(p, 0.99)))
    }

    val averagedP99 = pods.map { quantile(it, 0.99) }.average()
    val all = pods.flatMap { it.asList() }.toLongArray().also { it.sort() }   // what merging histograms gives you
    println()
    println("average of the ten p99s:  %.0f ms".format(averagedP99))
    println("p99 of all %,d requests: %d ms".format(all.size, quantile(all, 0.99)))
    println("service mean %.0f ms, p50 %d ms, p90 %d ms, p99.9 %d ms".format(
        all.average(), quantile(all, 0.5), quantile(all, 0.9), quantile(all, 0.999)))
}
