package sfz.batch.l11.demo

import java.io.File
import java.util.concurrent.ConcurrentSkipListSet
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread

/**
 * A reader counts rows in a loop while a writer adds 8 files. First into a plain Parquet folder,
 * one file a second, the way a job's tasks publish their files as they finish. Then into an
 * Iceberg table, as one commit. Prints every count the reader saw.
 */
fun main() {
    val spark = demoSpark()
    val staged = File("build/l09/staged").apply { deleteRecursively() }
    payments(spark, 0, 8_000, files = 8).write().parquet(staged.absolutePath)      // 8 files of 1,000 rows
    val files = staged.listFiles { f -> f.name.endsWith(".parquet") }!!.sorted()

    fun watch(count: () -> Long, write: () -> Unit): Set<Long> {
        val seen = ConcurrentSkipListSet<Long>()
        val done = AtomicBoolean(false)
        val reader = thread { while (!done.get()) runCatching { seen += count() } }
        Thread.sleep(500)
        write()
        Thread.sleep(500)
        done.set(true)
        reader.join()
        return seen
    }

    // a folder table: the file listing IS the table, so every new file is visible the moment it lands
    val folder = File("build/l09/plain").apply { deleteRecursively(); mkdirs() }
    val schema = spark.read().parquet(staged.absolutePath).schema()
    val plain = watch({ spark.read().schema(schema).parquet(folder.absolutePath).count() }) {
        for (f in files) {
            // copy under a hidden name, then rename: each single file appears whole
            val tmp = File(folder, ".${f.name}.tmp")
            f.copyTo(tmp)
            tmp.renameTo(File(folder, f.name))
            Thread.sleep(1_000)                                          // a task finishing every second
        }
    }
    println("plain folder, 8 files added one by one, the reader saw: $plain")

    // an Iceberg table: the files are written first, then one commit makes all of them visible
    spark.sql("CREATE TABLE lake.pay.atomic ($PAYMENT_COLUMNS) USING iceberg")
    val iceberg = watch({ spark.table("lake.pay.atomic").count() }) {
        repeat(3) { spark.read().parquet(staged.absolutePath).writeTo("lake.pay.atomic").append() }
    }
    println("Iceberg table, 3 commits of 8 files each, the reader saw: $iceberg")
    spark.stop()
}
