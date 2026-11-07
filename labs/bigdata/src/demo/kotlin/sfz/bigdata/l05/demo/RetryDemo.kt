package sfz.bigdata.l05.demo

import org.apache.logging.log4j.Level
import org.apache.logging.log4j.core.config.Configurator
import org.apache.spark.TaskContext
import org.apache.spark.api.java.JavaSparkContext
import org.apache.spark.scheduler.SparkListener
import org.apache.spark.scheduler.SparkListenerTaskEnd
import scala.Tuple2

/**
 * Shows an RDD's lineage, then makes one task fail on its first attempt and watches Spark run that
 * task again from the same lineage. `local[2,4]` means 2 slots and up to 4 attempts per task.
 */
fun main() {
    val spark = demoSpark("local[2,4]")
    Configurator.setLevel("org.apache.spark.executor.Executor", Level.OFF)   // no stack trace for the planned crash
    val sc = JavaSparkContext(spark.sparkContext())
    spark.sparkContext().addSparkListener(object : SparkListener() {
        override fun onTaskEnd(taskEnd: SparkListenerTaskEnd) {
            val info = taskEnd.taskInfo()
            println("  stage %d, partition %d, attempt %d: %s".format(
                taskEnd.stageId(), info.index(), info.attemptNumber(), if (info.successful()) "ok" else "FAILED (${taskEnd.reason().javaClass.simpleName})"))
        }
    })

    // per merchant: how many payments, from 4 partitions of made-up (merchant, amount) pairs
    val counts = sc.parallelize((0 until 40_000).toList(), 4)
        .map { i ->
            // partition 2 crashes the first time it runs, like a machine that dies mid-task
            if (TaskContext.getPartitionId() == 2 && TaskContext.get().attemptNumber() == 0) error("executor lost")
            i % 5
        }
        .mapToPair { m -> Tuple2(m, 1) }
        .reduceByKey { a, b -> a + b }

    println("lineage:")
    println(counts.toDebugString().lines().joinToString("\n") { "  " + it.replace(Regex(""" at \w+\.kt:\d+ \[]"""), "") })
    println("running:")
    val result = counts.collectAsMap().toSortedMap()
    spark.sparkContext().listenerBus().waitUntilEmpty()
    println("result: $result")
    spark.stop()
}
