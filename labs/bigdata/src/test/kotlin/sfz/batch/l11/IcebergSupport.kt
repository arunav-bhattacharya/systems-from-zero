package sfz.batch.l11

import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.ObjectMapper
import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import sfz.bigdata.support.LocalSpark
import sfz.bigdata.support.TestData
import java.io.File

/** A session with an Iceberg catalog named `l11` whose warehouse is [warehouse] (a Hadoop catalog: plain files). */
fun icebergSession(warehouse: File): SparkSession = LocalSpark.isolated(
    "spark.sql.catalog.l11" to "org.apache.iceberg.spark.SparkCatalog",
    "spark.sql.catalog.l11.type" to "hadoop",
    "spark.sql.catalog.l11.warehouse" to warehouse.absolutePath,
)

/** [n] payments from payment id [from], spread over 3 days, without the Hive-style `dt` column. */
fun batch(spark: SparkSession, from: Int, n: Int): Dataset<Row> {
    val rows = TestData.payments(from + n, days = 3).drop(from)
    return TestData.paymentsFrame(spark, rows).drop("dt").repartition(2)
}

/** The parsed JSON of a metadata file. */
fun json(file: File): JsonNode = ObjectMapper().readTree(file)

/** The field id of column [name] in the current schema of [metadata]. */
fun fieldId(metadata: JsonNode, name: String): Int {
    val schemaId = metadata.path("current-schema-id").asInt()
    val schema = metadata.path("schemas").first { it.path("schema-id").asInt() == schemaId }
    return schema.path("fields").firstOrNull { it.path("name").asText() == name }?.path("id")?.asInt() ?: -1
}

/** Every Parquet file under the table's data folder, as paths. */
fun dataFilesOnDisk(tableDir: File): Set<String> =
    File(tableDir, "data").walkTopDown().filter { it.isFile && it.name.endsWith(".parquet") }.map { it.absolutePath }.toSet()

/** The table's current metadata file, found the way a Hadoop catalog finds it: version-hint.text names it. */
fun currentMetadata(tableDir: File): File =
    File(tableDir, "metadata/v${File(tableDir, "metadata/version-hint.text").readText().trim()}.metadata.json")
