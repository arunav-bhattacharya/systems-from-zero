package sfz.bigdata.l10.demo

import java.io.File
import java.time.LocalDateTime
import java.time.ZoneOffset

/**
 * Old snapshots keep old files alive. Builds a table with five commits and a compaction, counts
 * the files on disk, expires every snapshot but the newest, and counts again. Then plants two
 * files no snapshot lists and runs remove_orphan_files.
 */
fun main() {
    val spark = demoSpark()
    val table = "lake.pay.ledger"
    val dir = tableDir("pay", "ledger")
    spark.sql("CREATE TABLE $table ($PAYMENT_COLUMNS) USING iceberg PARTITIONED BY (days(created_at))")
    repeat(5) { b -> payments(spark, b * 1_000L, 1_000).writeTo(table).append() }     // 5 commits, 3 files each
    val oldest = spark.sql("SELECT snapshot_id FROM $table.snapshots ORDER BY committed_at LIMIT 1").first().getLong(0)
    spark.sql("CALL lake.system.rewrite_data_files(table => 'pay.ledger', options => map('min-input-files', '2'))").collect()

    fun census(label: String) {
        val snapshots = spark.sql("SELECT count(*) FROM $table.snapshots").first().getLong(0)
        val live = spark.sql("SELECT count(*) FROM $table.data_files").first().getLong(0)
        val onDisk = dataFolderFiles(dir).count { it.name.endsWith(".parquet") }
        println("$label: $snapshots snapshots; the current one lists $live data files; data/ holds $onDisk Parquet files")
    }
    census("after 5 appends and a compaction")
    println("time travel to the first snapshot: ${spark.sql("SELECT count(*) FROM $table VERSION AS OF $oldest").first().getLong(0)} rows")

    val now = LocalDateTime.now(ZoneOffset.UTC).withNano(0).toString().replace('T', ' ')
    val r = spark.sql("CALL lake.system.expire_snapshots(table => 'pay.ledger', older_than => TIMESTAMP '$now', retain_last => 1)").first()
    println("expire_snapshots: deleted ${r.getAs<Long>("deleted_data_files_count")} data files, " +
        "${r.getAs<Long>("deleted_manifest_files_count")} manifests, ${r.getAs<Long>("deleted_manifest_lists_count")} manifest lists")
    census("after expire_snapshots")
    val travel = runCatching { spark.sql("SELECT count(*) FROM $table VERSION AS OF $oldest").collect() }
    println("time travel to the first snapshot: ${travel.exceptionOrNull()?.message?.lineSequence()?.first() ?: "still works"}")

    // two files that no snapshot lists: one left by a job that crashed 3 days ago, one being written right now
    val day = File(dir, "data").listFiles()!!.first { it.isDirectory }
    File(day, "00099-crashed-job.parquet").apply { writeText("half a file") }.setLastModified(System.currentTimeMillis() - 3 * 86_400_000L)
    File(day, "00100-job-still-running.parquet").writeText("being written")
    val refused = runCatching { spark.sql("CALL lake.system.remove_orphan_files(table => 'pay.ledger', older_than => TIMESTAMP '$now')").collect() }
    println("remove_orphan_files, older than now: ${refused.exceptionOrNull()?.message?.substringBefore(". ")}.")
    val dayAgo = LocalDateTime.now(ZoneOffset.UTC).minusDays(1).withNano(0).toString().replace('T', ' ')
    val removed = spark.sql("CALL lake.system.remove_orphan_files(table => 'pay.ledger', older_than => TIMESTAMP '$dayAgo')").collectAsList()
    println("remove_orphan_files, older than a day: removed " + removed.map { File(it.getString(0)).name })
    println("still in ${day.name}/: " + day.list()!!.filter { !it.startsWith(".") }.map { if ("job" in it) it else short(it) }.sorted())
    spark.stop()
}
