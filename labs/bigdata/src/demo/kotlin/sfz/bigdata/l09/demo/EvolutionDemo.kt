package sfz.bigdata.l09.demo

import org.apache.hadoop.fs.Path
import org.apache.iceberg.expressions.Expressions
import org.apache.iceberg.spark.Spark3Util
import org.apache.parquet.hadoop.ParquetFileReader
import org.apache.parquet.hadoop.util.HadoopInputFile
import java.io.File

/**
 * Hidden partitioning, schema evolution and partition evolution on one table, and a format v3
 * table for comparison.
 */
fun main() {
    val spark = demoSpark()
    val name = "lake.pay.evolving"
    spark.sql("CREATE TABLE $name ($PAYMENT_COLUMNS) USING iceberg PARTITIONED BY (days(created_at))")
    payments(spark, 0, 3_000).writeTo(name).append()
    val dir = tableDir("pay", "evolving")
    fun dataFiles() = File(dir, "data").walkTopDown().filter { it.isFile && it.name.endsWith(".parquet") }.toList()
    println("data folders: " + File(dir, "data").list()!!.sorted())

    // hidden partitioning: filter on created_at, and Iceberg works out which day folders can match
    val table = Spark3Util.loadIcebergTable(spark, name)
    val all = table.newScan().planFiles().use { it.count() }
    val nov2 = table.newScan().filter(Expressions.and(
        Expressions.greaterThanOrEqual("created_at", "2026-11-02T00:00:00+00:00"),
        Expressions.lessThan("created_at", "2026-11-03T00:00:00+00:00"))).planFiles().use { it.count() }
    println("WHERE created_at on 2026-11-02 plans $nov2 of $all data files")

    // schema evolution: the Parquet files store a field id next to every column name
    val file = dataFiles().first()
    val footer = ParquetFileReader.open(HadoopInputFile.fromPath(Path(file.absolutePath), spark.sparkContext().hadoopConfiguration())).use { it.footer }
    println("a data file's Parquet schema: " + footer.fileMetaData.schema.toString().replace("\n", " ").replace(Regex(" +"), " "))
    val before = dataFiles().map { it.name }.toSet()
    spark.sql("ALTER TABLE $name RENAME COLUMN amount_cents TO amount_minor")
    spark.sql("ALTER TABLE $name ADD COLUMN risk_score DOUBLE")
    spark.sql("ALTER TABLE $name DROP COLUMN status")
    println("after rename, add and drop: data files rewritten: ${(before - dataFiles().map { it.name }.toSet()).size}")
    println("columns now: " + spark.table(name).columns().joinToString())
    println("first row now: " + spark.table(name).orderBy("payment_id").first())

    // partition evolution: new data also buckets by merchant; old files keep the old layout
    spark.sql("ALTER TABLE $name ADD PARTITION FIELD bucket(4, merchant_id)")
    payments(spark, 3_000, 1_000).withColumnRenamed("amount_cents", "amount_minor").drop("status").writeTo(name).append()
    spark.sql("SELECT spec_id, count(*) AS files, sum(record_count) AS rows FROM $name.files GROUP BY spec_id ORDER BY spec_id").collectAsList()
        .forEach { println("partition spec ${it.getInt(0)}: ${it.getLong(1)} files, ${it.getLong(2)} rows") }
    println("a new data folder: " + dataFiles().map { it.parentFile.relativeTo(File(dir, "data")).path }.filter { "bucket" in it }.sorted().first())

    // the newest format version, for comparison
    spark.sql("CREATE TABLE lake.pay.v3 ($PAYMENT_COLUMNS) USING iceberg TBLPROPERTIES ('format-version' = '3')")
    payments(spark, 0, 100).writeTo("lake.pay.v3").append()
    val v3 = json(File(tableDir("pay", "v3"), "metadata/v2.metadata.json"))
    println("lake.pay.v3: format-version ${v3.path("format-version")}, next-row-id ${v3.path("next-row-id")}")
    println("v3 row lineage: " + spark.sql("SELECT payment_id, _row_id, _last_updated_sequence_number FROM lake.pay.v3 ORDER BY payment_id LIMIT 2").collectAsList())
    spark.stop()
}
