package sfz.bigdata.support

import org.apache.spark.scheduler.SparkListener
import org.apache.spark.scheduler.SparkListenerJobStart
import org.apache.spark.scheduler.SparkListenerStageCompleted
import org.apache.spark.scheduler.SparkListenerTaskEnd
import org.apache.spark.sql.SparkSession
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.ConcurrentSkipListMap
import java.util.concurrent.atomic.AtomicInteger

/**
 * What Spark actually ran for one action, as its scheduler reported it. Stages that Spark skipped
 * (because their shuffle output already existed) are not counted.
 */
data class RunStats(
    val jobs: Int,
    /** Tasks per completed stage, in stage id order. */
    val stageTasks: List<Int>,
    /** Records and bytes all stages wrote to shuffle files. */
    val shuffleRecordsWritten: Long,
    val shuffleBytesWritten: Long,
    /**
     * For every completed stage, in stage id order, the shuffle records each of its tasks fetched
     * (sorted, largest last). A stage that reads no shuffle has all zeros. Lesson 7 uses it to spot
     * one task that reads far more than the others: skew.
     */
    val shuffleReadPerTask: List<List<Long>> = emptyList(),
) {
    val stages get() = stageTasks.size
    val tasks get() = stageTasks.sum()

    /** The most shuffle records any single task fetched: the straggler's load. */
    val maxTaskShuffleRead: Long get() = shuffleReadPerTask.flatten().maxOrNull() ?: 0L
}

/** Counts the jobs, stages and tasks one action runs, using a listener on the SparkContext. */
object Jobs {
    /**
     * Runs [action] and returns its result with what the scheduler ran for it. Waits for Spark's
     * listener bus to deliver every event first, so the counts are complete. Tests run one at a
     * time, so nothing else runs jobs while this measures.
     */
    fun <T> measure(spark: SparkSession, action: () -> T): Pair<T, RunStats> {
        val bus = spark.sparkContext().listenerBus()
        bus.waitUntilEmpty()                       // events from earlier actions must not count
        val jobs = AtomicInteger()
        val stages = ConcurrentSkipListMap<Int, Triple<Int, Long, Long>>()
        val taskReads = ConcurrentSkipListMap<Int, ConcurrentLinkedQueue<Long>>()
        val listener = object : SparkListener() {
            override fun onJobStart(jobStart: SparkListenerJobStart) {
                jobs.incrementAndGet()
            }

            override fun onStageCompleted(stageCompleted: SparkListenerStageCompleted) {
                val info = stageCompleted.stageInfo()
                val write = info.taskMetrics().shuffleWriteMetrics()
                stages[info.stageId()] = Triple(info.numTasks(), write.recordsWritten(), write.bytesWritten())
            }

            override fun onTaskEnd(taskEnd: SparkListenerTaskEnd) {
                val read = taskEnd.taskMetrics()?.shuffleReadMetrics()?.recordsRead() ?: return
                taskReads.computeIfAbsent(taskEnd.stageId()) { ConcurrentLinkedQueue() }.add(read)
            }
        }
        spark.sparkContext().addSparkListener(listener)
        try {
            val result = action()
            bus.waitUntilEmpty()
            return result to RunStats(
                jobs = jobs.get(),
                stageTasks = stages.values.map { it.first },
                shuffleRecordsWritten = stages.values.sumOf { it.second },
                shuffleBytesWritten = stages.values.sumOf { it.third },
                shuffleReadPerTask = stages.keys.map { id -> taskReads[id]?.sorted() ?: emptyList() },
            )
        } finally {
            spark.sparkContext().removeSparkListener(listener)
        }
    }
}
