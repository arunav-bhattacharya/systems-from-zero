package sfz.bigdata.l05.demo

import org.apache.spark.TaskContext
import org.apache.spark.api.java.function.MapPartitionsFunction
import org.apache.spark.sql.Encoders

/**
 * Runs one stage of 8 tasks, each of which works for 300 ms, first with 2 task slots and then
 * with 4. Every task reports its partition and when it started; tasks that started together are
 * one wave.
 */
fun main() {
    val tasks = 8                                               // try 9
    for (slots in listOf(2, 4)) {
        val spark = demoSpark("local[$slots]")
        val task = MapPartitionsFunction<Long, String> { _ ->
            val start = System.currentTimeMillis()
            Thread.sleep(300)                                   // pretend to read and filter 300 ms of data
            listOf("${TaskContext.getPartitionId()} $start").iterator()
        }
        spark.range(0, tasks.toLong(), 1, tasks).mapPartitions(task, Encoders.STRING()).collectAsList()   // warm-up: the first job pays for class loading
        val t0 = System.nanoTime()
        val started = spark.range(0, tasks.toLong(), 1, tasks).mapPartitions(task, Encoders.STRING()).collectAsList()
            .map { it.split(" ").let { (p, t) -> p.toInt() to t.toLong() } }
        val ms = (System.nanoTime() - t0) / 1_000_000
        println("local[$slots]: $tasks tasks of 300 ms each took $ms ms")
        val first = started.minOf { it.second }
        // tasks that started within 100 ms of each other ran side by side: one wave
        val waves = started.sortedBy { it.second }.fold(mutableListOf<MutableList<Pair<Int, Long>>>()) { acc, t ->
            if (acc.isEmpty() || t.second - acc.last().first().second > 100) acc += mutableListOf(t) else acc.last() += t
            acc
        }
        waves.forEachIndexed { i, w ->
            println("  wave %d starts at %4d ms: partitions %s".format(i + 1, w.first().second - first, w.map { it.first }.sorted().joinToString(", ")))
        }
        spark.stop()
    }
}
