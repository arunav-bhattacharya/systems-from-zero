package sfz.bigdata.l09.demo

import org.apache.avro.generic.GenericRecord
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Creates an Iceberg table, commits three appends, then walks its metadata tree from disk:
 * version-hint.text, the metadata JSON, the manifest list, and one manifest with its column stats.
 */
fun main() {
    val spark = demoSpark()
    spark.sql("CREATE TABLE lake.pay.payments ($PAYMENT_COLUMNS) USING iceberg PARTITIONED BY (days(created_at))")
    for (b in 0 until 3) payments(spark, b * 1_000L, 1_000).writeTo("lake.pay.payments").append()
    val dir = tableDir("pay", "payments")

    println("metadata/ holds:")
    File(dir, "metadata").listFiles { f -> !f.name.startsWith(".") }!!.sortedBy { it.name }.forEach {
        println("  %-60s %,6d bytes".format(it.name.replace(Regex("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"), "<uuid>"), it.length()))
    }
    val version = File(dir, "metadata/version-hint.text").readText().trim()
    println("version-hint.text says: $version")

    val meta = json(File(dir, "metadata/v$version.metadata.json"))
    val current = meta.path("current-snapshot-id").asLong()
    println("v$version.metadata.json: format-version ${meta.path("format-version")}, current-snapshot-id $current, " +
        "partition spec ${meta.path("partition-specs")[0].path("fields")}")
    for (s in meta.path("snapshots")) {
        val sum = s.path("summary")
        println("  snapshot %d parent %-20s added %s files, table now %s rows, manifest list %s".format(
            s.path("snapshot-id").asLong(), s.path("parent-snapshot-id").asText("none"),
            sum.path("added-data-files").asText(), sum.path("total-records").asText(),
            File(s.path("manifest-list").asText()).name.take(20) + "..."))
    }

    val list = meta.path("snapshots").first { it.path("snapshot-id").asLong() == current }.path("manifest-list").asText()
    println("the current manifest list names ${avro(list).size} manifests:")
    for (m in avro(list)) {
        println("  %s  added_files %s existing_files %s".format(
            File(m.get("manifest_path").toString()).name.take(14) + "...", m.get("added_files_count"), m.get("existing_files_count")))
    }

    val newest = avro(list).first().get("manifest_path").toString()
    val amountId = meta.path("schemas")[0].path("fields").first { it.path("name").asText() == "amount_cents" }.path("id").asInt()
    println("one manifest, ${avro(newest).size} entries (amount_cents is field $amountId):")
    for (e in avro(newest)) {
        val f = e.get("data_file") as GenericRecord
        @Suppress("UNCHECKED_CAST")
        fun bound(name: String): Long =
            ((f.get(name) as List<GenericRecord>).first { it.get("key") == amountId }.get("value") as ByteBuffer)
                .duplicate().order(ByteOrder.LITTLE_ENDIAN).long
        println("  status %s  %-64s rows %s  amount_cents %,d..%,d".format(
            e.get("status"), rel(dir, f.get("file_path").toString()).replace(Regex("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"), "<uuid>"),
            f.get("record_count"), bound("lower_bounds"), bound("upper_bounds")))
    }
    spark.stop()
}
