package sfz.bigdata.l03.demo

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions.col
import java.io.File

/**
 * Registers the lake from PartitionPruningDemo as a table in Spark's catalog, which plays the Hive
 * metastore here, and shows that the catalog's partition list and the directories can disagree.
 */
fun main() {
    val lake = File("build/l03/lake")
    val spark = demoSpark()
    File(lake, "dt=2026-11-08").deleteRecursively()                  // left over from an earlier run
    if (!File(lake, "_SUCCESS").exists()) {
        demoPayments(spark).write().mode(SaveMode.Overwrite).partitionBy("dt").parquet(lake.absolutePath)
    }
    fun show(label: String, sql: String) = println("%-34s %s".format(label, spark.sql(sql).collectAsList().joinToString(" ") { it.mkString(",") }))

    // 1. register the existing directory as an external table: schema and location go into the catalog
    spark.sql("""
        CREATE TABLE payments (payment_id BIGINT, merchant_id INT, card_country STRING,
                               amount_cents BIGINT, created_at TIMESTAMP, dt STRING)
        USING parquet PARTITIONED BY (dt) LOCATION '${lake.absolutePath}'""")
    show("rows right after CREATE TABLE:", "SELECT count(*) FROM payments")

    // 2. the catalog has no partitions yet; MSCK REPAIR walks the directory and adds them
    spark.sql("MSCK REPAIR TABLE payments")
    show("rows after MSCK REPAIR TABLE:", "SELECT count(*) FROM payments")
    println("%-34s %d".format("partitions the catalog knows:", spark.sql("SHOW PARTITIONS payments").count()))

    // 3. a late job writes 2026-11-08 straight into the directory, without telling the catalog
    demoPayments(spark, days = 1, firstEpochSecond = 1_794_096_000L).drop("dt")
        .write().mode(SaveMode.Overwrite).parquet(File(lake, "dt=2026-11-08").absolutePath)
    show("rows for 2026-11-08, before:", "SELECT count(*) FROM payments WHERE dt = '2026-11-08'")
    spark.sql("ALTER TABLE payments ADD PARTITION (dt = '2026-11-08')")
    show("rows for 2026-11-08, after ADD:", "SELECT count(*) FROM payments WHERE dt = '2026-11-08'")

    // 4. a filter on dt is answered by the catalog first: only one day's files get opened
    val oneDay = spark.table("payments").where(col("dt").equalTo("2026-11-03"))
    println("files opened for dt = 2026-11-03:   %d of %d".format(oneDay.inputFiles().size, dataFiles(lake).size))
    spark.stop()
}
