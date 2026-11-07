package sfz.bigdata.l10.demo

import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.lit

/**
 * The same 30 refunds, applied with MERGE INTO to three copies of a 300,000-row payments table:
 * copy-on-write, merge-on-read on format v2 (position delete files) and merge-on-read on format v3
 * (deletion vectors). Prints what each commit wrote, then what a position delete file holds.
 */
fun main() {
    val spark = demoSpark()
    val modes = listOf(
        Triple("cow", "copy-on-write, v2", "'format-version' = '2', 'write.merge.mode' = 'copy-on-write'"),
        Triple("mor2", "merge-on-read, v2", "'format-version' = '2', 'write.merge.mode' = 'merge-on-read'"),
        Triple("mor3", "merge-on-read, v3", "'format-version' = '3', 'write.merge.mode' = 'merge-on-read'"),
    )
    // 30 refunds: payments 0, 1,000, 2,000, ... so 10 land on each of the 3 days
    spark.range(0, 30).select(col("id").multiply(1_000).alias("payment_id"), lit("REFUNDED").alias("status"))
        .createOrReplaceTempView("refunds")
    for ((name, label, props) in modes) {
        val table = "lake.pay.$name"
        spark.sql("CREATE TABLE $table ($PAYMENT_COLUMNS) USING iceberg PARTITIONED BY (days(created_at)) TBLPROPERTIES ($props)")
        payments(spark, 0, 300_000).writeTo(table).append()                 // one data file per day
        spark.sql("MERGE INTO $table t USING refunds r ON t.payment_id = r.payment_id WHEN MATCHED THEN UPDATE SET t.status = r.status")
        val s = lastSummary(spark, table)
        // the delete files the commit added: one row per position delete file, or per deletion vector
        val deletes = spark.sql("SELECT file_path, file_size_in_bytes FROM $table.delete_files").collectAsList()
        val deleteFiles = deletes.map { it.getString(0) to it.getLong(1) }.distinct()
        val deleteBytes = deleteFiles.sumOf { it.second }
        val dataBytes = s.getValue("added-files-size").toLong() - deleteBytes
        val vectors = if ((s["added-dvs"] ?: "0") != "0") " holding ${s["added-dvs"]} deletion vectors" else ""
        val deletesWritten = if (deleteFiles.isEmpty()) "no delete file" else "${files(deleteFiles.size, "delete")} (${size(deleteBytes)})$vectors"
        println("$label: wrote ${files(s.getValue("added-data-files").toInt(), "data")} (${size(dataBytes)}) and $deletesWritten")
        println("  dropped ${s["deleted-data-files"] ?: 0} data files from the snapshot, " +
            "copied ${"%,d".format(s.getValue("spark.merge-into.num-target-rows-copied").toLong())} unchanged rows")
        val dataFiles = spark.sql("SELECT count(*) FROM $table.data_files").first().getLong(0).toInt()
        println("  a reader now opens ${files(dataFiles, "data")} and ${files(deleteFiles.size, "delete")}; " +
            "refunded rows: ${spark.table(table).where("status = 'REFUNDED'").count()}")
    }
    // what a v2 position delete file holds: the data file and the row position, one row per deleted row
    val deleteFile = spark.sql("SELECT file_path FROM lake.pay.mor2.delete_files ORDER BY file_path LIMIT 1").first().getString(0)
    println("one position delete file, ${short(deleteFile)}:")
    spark.read().parquet(deleteFile).orderBy("pos").limit(3).collectAsList()
        .forEach { println("  file_path = ${short(it.getString(0))}, pos = ${it.getLong(1)}") }
    spark.stop()
}

private fun files(n: Int, kind: String) = "$n $kind file" + if (n == 1) "" else "s"
