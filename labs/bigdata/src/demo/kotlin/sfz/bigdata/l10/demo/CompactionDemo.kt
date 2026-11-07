package sfz.bigdata.l10.demo

import org.apache.iceberg.spark.Spark3Util
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.lit

/**
 * A merge-on-read table built the way a stream builds one: 12 small appends to the same day, then
 * 3 correction batches. Shows what a reader has to open, compacts with rewrite_data_files, and
 * shows it again.
 */
fun main() {
    val spark = demoSpark()
    val table = "lake.pay.stream"
    spark.sql("CREATE TABLE $table ($PAYMENT_COLUMNS) USING iceberg PARTITIONED BY (days(created_at)) " +
        "TBLPROPERTIES ('format-version' = '2', 'write.merge.mode' = 'merge-on-read')")
    // a stream that commits every few minutes: 12 commits of 5,000 payments, all on one day
    repeat(12) { b -> payments(spark, b * 5_000L, 5_000, days = 1).writeTo(table).append() }
    // three batches of refunds, each one MERGE: 3 more small data files and 3 delete files
    repeat(3) { c ->
        spark.range(0, 20).select(col("id").multiply(3_000).plus(c).alias("payment_id"), lit("REFUNDED").alias("status"))
            .createOrReplaceTempView("refunds")
        spark.sql("MERGE INTO $table t USING refunds r ON t.payment_id = r.payment_id WHEN MATCHED THEN UPDATE SET t.status = r.status")
    }
    report(spark, table, "before compaction")

    val r = spark.sql("""
        CALL lake.system.rewrite_data_files(
            table => 'pay.stream',
            options => map('min-input-files', '2', 'delete-file-threshold', '1', 'remove-dangling-deletes', 'true'))
        """).first()
    println("rewrite_data_files: rewrote ${r.getAs<Int>("rewritten_data_files_count")} data files " +
        "(${size(r.getAs<Long>("rewritten_bytes_count"))}) into ${r.getAs<Int>("added_data_files_count")}, " +
        "removed ${r.getAs<Int>("removed_delete_files_count")} delete files")
    report(spark, table, "after compaction")
    spark.stop()
}

private fun report(spark: SparkSession, table: String, label: String) {
    val sizes = spark.sql("SELECT file_size_in_bytes FROM $table.data_files").collectAsList().map { it.getLong(0) }
    val deletes = spark.sql("SELECT count(*) FROM $table.delete_files").first().getLong(0)
    // what a reader plans: one task per data file, each carrying the delete files it must apply
    val tasks = Spark3Util.loadIcebergTable(spark, table).newScan().planFiles().use { it.toList() }
    val deletesToApply = tasks.sumOf { it.deletes().size }
    val ops = spark.sql("SELECT operation FROM $table.snapshots ORDER BY committed_at").collectAsList().map { it.getString(0) }
    val opCounts = ops.groupingBy { it }.eachCount().entries.joinToString { "${it.value} ${it.key}" }
    println("$label: ${ops.size} snapshots ($opCounts), ${count(sizes.size, "data file")} averaging ${size(sizes.average().toLong())}, " +
        count(deletes.toInt(), "delete file"))
    println("  a full scan plans ${count(tasks.size, "file task")}, which must apply ${count(deletesToApply, "delete file")}")
    println("  rows: " + spark.sql("SELECT status, count(*) FROM $table GROUP BY status ORDER BY status").collectAsList().joinToString { "${it.getString(0)} ${it.getLong(1)}" })
}

private fun count(n: Int, what: String) = "$n $what" + if (n == 1) "" else "s"
