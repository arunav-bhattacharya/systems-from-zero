package sfz.bigdata.l06

import org.apache.spark.scheduler.SparkListener
import org.apache.spark.scheduler.SparkListenerTaskEnd
import java.util.concurrent.atomic.AtomicLong

/**
 * Adds up shuffle traffic, task by task. Register it with
 * `spark.sparkContext().addSparkListener(meter)`. Spark calls [onTaskEnd] on its listener thread
 * after every task of every job, with the task's metrics.
 */
class ShuffleMeter : SparkListener() {
    private val bytesOut = AtomicLong()
    private val recordsOut = AtomicLong()
    private val bytesIn = AtomicLong()
    private val recordsIn = AtomicLong()

    /** Bytes map tasks wrote to shuffle files on local disk. */
    val bytesWritten: Long get() = bytesOut.get()

    /** Rows map tasks wrote to shuffle files. */
    val recordsWritten: Long get() = recordsOut.get()

    /** Bytes reduce tasks fetched from shuffle files, local and remote. */
    val bytesRead: Long get() = bytesIn.get()

    /** Rows reduce tasks fetched from shuffle files. */
    val recordsRead: Long get() = recordsIn.get()

    /**
     * Add this task's shuffle numbers to the totals. `taskEnd.taskMetrics()` can be null for a task
     * that failed. Its `shuffleWriteMetrics()` has `bytesWritten()` and `recordsWritten()`; its
     * `shuffleReadMetrics()` has `totalBytesRead()` and `recordsRead()`.
     */
    override fun onTaskEnd(taskEnd: SparkListenerTaskEnd) {
        TODO("read the task's shuffle write and read metrics and add them up")
    }

    /** Start counting from zero again. */
    fun reset() {
        listOf(bytesOut, recordsOut, bytesIn, recordsIn).forEach { it.set(0) }
    }
}
