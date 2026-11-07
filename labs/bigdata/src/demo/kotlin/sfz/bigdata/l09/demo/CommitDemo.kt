package sfz.bigdata.l09.demo

import org.apache.iceberg.HasTableOperations
import org.apache.iceberg.TableMetadata
import org.apache.iceberg.exceptions.CommitFailedException
import org.apache.iceberg.hadoop.HadoopTables

/**
 * Two writers start from the same version of a table. The first commit wins the swap; the second
 * is refused, then retried on top of the new version. Then time travel.
 */
fun main() {
    val spark = demoSpark()
    spark.sql("CREATE TABLE lake.pay.ledger ($PAYMENT_COLUMNS) USING iceberg PARTITIONED BY (days(created_at))")
    payments(spark, 0, 1_000).writeTo("lake.pay.ledger").append()
    val firstCommitAt = System.currentTimeMillis()
    Thread.sleep(50)
    val location = tableDir("pay", "ledger").absolutePath
    val tables = HadoopTables(spark.sparkContext().hadoopConfiguration())

    // two writers load the table: both see the same current version
    val tableA = tables.load(location)
    val tableB = tables.load(location)
    val a = (tableA as HasTableOperations).operations()
    val b = (tableB as HasTableOperations).operations()
    val baseA = a.current()
    val baseB = b.current()
    println("writer A and writer B both start from ${baseA.metadataFileLocation().substringAfterLast('/')}")

    // the low-level commit: "replace base with this new metadata", a compare-and-swap
    a.commit(baseA, TableMetadata.buildFrom(baseA).setProperties(mapOf("settlement.run" to "A")).build())
    println("A commits: the table is now at ${a.current().metadataFileLocation().substringAfterLast('/')}")
    try {
        b.commit(baseB, TableMetadata.buildFrom(baseB).setProperties(mapOf("settlement.run" to "B")).build())
    } catch (e: CommitFailedException) {
        println("B commits from the old base: CommitFailedException: ${e.message!!.substringBefore(": /")}")
    }

    // the normal API, on B's same stale table object: it reloads the current version, applies
    // the change to it and swaps; if the swap loses again, it repeats (commit.retry.num-retries)
    tableB.updateProperties().set("settlement.run", "B").commit()
    val now = tables.load(location)
    println("B retries on top of A: the table is at ${(now as HasTableOperations).operations().current().metadataFileLocation().substringAfterLast('/')}, " +
        "settlement.run = ${now.properties()["settlement.run"]}")

    // two more appends, then read the past
    payments(spark, 1_000, 500).writeTo("lake.pay.ledger").append()
    payments(spark, 1_500, 500).writeTo("lake.pay.ledger").append()
    val history = spark.sql("SELECT snapshot_id, parent_id, operation FROM lake.pay.ledger.snapshots ORDER BY committed_at").collectAsList()
    println("snapshots: " + history.joinToString { "${it.getLong(0)} (${it.getString(2)})" })
    println("now: %,d rows".format(spark.table("lake.pay.ledger").count()))
    println("VERSION AS OF the first snapshot: %,d rows".format(
        spark.sql("SELECT count(*) FROM lake.pay.ledger VERSION AS OF ${history.first().getLong(0)}").first().getLong(0)))
    println("TIMESTAMP AS OF just after the first commit: %,d rows".format(
        spark.sql("SELECT count(*) FROM lake.pay.ledger TIMESTAMP AS OF CAST($firstCommitAt / 1000.0 AS TIMESTAMP)").first().getLong(0)))
    spark.stop()
}
