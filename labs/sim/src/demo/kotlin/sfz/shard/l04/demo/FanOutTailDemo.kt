package sfz.shard.l04.demo

import java.util.Random

/** Each shard answers in 2 to 3 ms, except 1 time in 100 it takes 50 ms. A scatter-gather waits for the slowest. */
fun main() {
    val rnd = Random(42)
    fun shardMillis() = if (rnd.nextInt(100) == 0) 50.0 else 2.0 + rnd.nextDouble()
    fun pct(sorted: List<Double>, p: Double) = sorted[maxOf(0, Math.ceil(p / 100 * sorted.size).toInt() - 1)]
    println("shards asked   p50 ms   p90 ms   p99 ms   queries over 10 ms   1 - 0.99^shards")
    for (shards in listOf(1, 2, 5, 10, 20, 50, 100)) {
        val q = List(20_000) { (1..shards).maxOf { shardMillis() } }.sorted()
        val slow = q.count { it > 10.0 } / 200.0
        println("%12d   %6.1f   %6.1f   %6.1f   %17.1f%%   %14.1f%%".format(
            shards, pct(q, 50.0), pct(q, 90.0), pct(q, 99.0), slow, (1 - Math.pow(0.99, shards.toDouble())) * 100))
    }
}
