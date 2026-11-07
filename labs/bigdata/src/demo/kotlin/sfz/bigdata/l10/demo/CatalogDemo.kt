package sfz.bigdata.l10.demo

import org.apache.iceberg.HasTableOperations
import org.apache.iceberg.TableMetadata
import org.apache.iceberg.catalog.TableIdentifier
import org.apache.iceberg.exceptions.CommitFailedException
import org.apache.iceberg.spark.Spark3Util
import java.io.File
import java.sql.DriverManager

/**
 * An Iceberg JDBC catalog whose database is one SQLite file. Prints the catalog's row for the
 * table after each commit, then shows a commit from a stale version being refused.
 */
fun main() {
    val db = File("build/l10/catalog.db").apply { delete() }
    val spark = demoSpark(
        "spark.sql.catalog.shop" to "org.apache.iceberg.spark.SparkCatalog",
        "spark.sql.catalog.shop.type" to "jdbc",
        "spark.sql.catalog.shop.uri" to "jdbc:sqlite:${db.absolutePath}",
        "spark.sql.catalog.shop.warehouse" to File(WAREHOUSE, "shop").absolutePath,
    )
    fun catalogRow(label: String) = DriverManager.getConnection("jdbc:sqlite:${db.absolutePath}").use { c ->
        c.createStatement().executeQuery(
            "SELECT table_namespace, table_name, metadata_location, previous_metadata_location FROM iceberg_tables"
        ).use { rs ->
            while (rs.next()) {
                fun name(i: Int) = rs.getString(i)?.substringAfterLast('/')?.replace(Regex("^(\\d+)-[0-9a-f-]{36}"), "$1-<uuid>") ?: "null"
                println("$label: ${rs.getString(1)}.${rs.getString(2)} -> ${name(3)} (previous: ${name(4)})")
            }
        }
    }

    spark.sql("CREATE TABLE shop.pay.payments ($PAYMENT_COLUMNS) USING iceberg PARTITIONED BY (days(created_at))")
    catalogRow("after CREATE TABLE")
    payments(spark, 0, 1_000).writeTo("shop.pay.payments").append()
    catalogRow("after the 1st append")
    payments(spark, 1_000, 1_000).writeTo("shop.pay.payments").append()
    catalogRow("after the 2nd append")

    // two writers load the same version; A commits first, then B tries from its stale base
    val catalog = Spark3Util.loadIcebergCatalog(spark, "shop")
    val id = TableIdentifier.of("pay", "payments")
    val a = (catalog.loadTable(id) as HasTableOperations).operations()
    val b = (catalog.loadTable(id) as HasTableOperations).operations()
    val baseA = a.current()
    val baseB = b.current()
    a.commit(baseA, TableMetadata.buildFrom(baseA).setProperties(mapOf("owner" to "settlement")).build())
    catalogRow("after writer A's commit")
    try {
        b.commit(baseB, TableMetadata.buildFrom(baseB).setProperties(mapOf("owner" to "fraud")).build())
    } catch (e: CommitFailedException) {
        println("writer B, from the old version: CommitFailedException: ${e.message!!.replace(Regex("/\\S+/"), "")}")
    }
    catalogRow("after writer B's attempt")
    println("rows: %,d".format(spark.table("shop.pay.payments").count()))
    spark.stop()
}
