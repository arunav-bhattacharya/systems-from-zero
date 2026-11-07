package sfz.bigdata.l08.demo

import org.apache.spark.sql.SaveMode
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.concat
import org.apache.spark.sql.functions.element_at
import org.apache.spark.sql.functions.array
import org.apache.spark.sql.functions.hash
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.pmod
import org.apache.spark.unsafe.types.VariantVal
import java.io.File

/**
 * Webhook events as JSON text and as VARIANT: what one variant holds, how fields come out of it,
 * and the same question asked of 300,000 events stored both ways in Parquet.
 */
fun main() {
    val spark = demoSpark()
    val body = """{"type":"authorization","amount":1250,"card":{"country":"NL","bin":"411111"},"risk":{"score":0.93,"rules":["velocity","geo"]}}"""
    val one = spark.sql("SELECT parse_json('$body') AS event")
    val v = one.first().get(0) as VariantVal
    println("JSON text: ${body.length} bytes; the variant: ${v.metadata.size} bytes of field names + ${v.value.size} bytes of values")
    println("schema_of_variant: " + one.selectExpr("schema_of_variant(event)").first().getString(0))
    println("event:card.country::string -> " + one.selectExpr("event:card.country::string").first().getString(0))
    println("variant_get(event, '$.risk.score', 'double') -> " + one.selectExpr("variant_get(event, '$.risk.score', 'double')").first().get(0))
    println("to_json(parse_json('{\"b\":1,\"a\":2}')) -> " + spark.sql("SELECT to_json(parse_json('{\"b\":1,\"a\":2}'))").first().getString(0))

    // 300,000 events: write them once as text and once as variant
    val text = File("build/l08/events-text")
    val variant = File("build/l08/events-variant")
    if (!File(variant, "_SUCCESS").exists()) {
        val events = spark.range(0, 300_000, 1, 4).select(
            col("id").alias("event_id"),
            concat(
                lit("""{"type":"authorization","amount":"""), pmod(hash(col("id")), lit(250_000)).cast("string"),
                lit(""","card":{"country":""""),
                element_at(array(lit("NL"), lit("DE"), lit("FR"), lit("GB")), pmod(hash(col("id"), lit(1)), lit(4)).plus(1)),
                lit(""""},"risk":{"score":"""), pmod(hash(col("id"), lit(2)), lit(100)).divide(100).cast("string"),
                lit(""","rules":["velocity"]},"merchant":{"id":"""), pmod(hash(col("id"), lit(3)), lit(500)).cast("string"),
                lit(""","name":"Merchant shop"}}"""),
            ).alias("body"),
        )
        events.write().mode(SaveMode.Overwrite).parquet(text.absolutePath)
        spark.read().parquet(text.absolutePath).selectExpr("event_id", "parse_json(body) AS event")
            .write().mode(SaveMode.Overwrite).parquet(variant.absolutePath)
    }
    fun size(dir: File) = dir.listFiles { f -> f.name.endsWith(".parquet") }!!.sumOf { it.length() }
    println("on disk: text %,d bytes, variant %,d bytes".format(size(text), size(variant)))

    spark.read().parquet(text.absolutePath).createOrReplaceTempView("events_text")
    spark.read().parquet(variant.absolutePath).createOrReplaceTempView("events_variant")
    val asText = """SELECT get_json_object(body, '$.card.country') AS country, count(*) AS high_risk
                    FROM events_text WHERE CAST(get_json_object(body, '$.risk.score') AS DOUBLE) > 0.8 GROUP BY 1 ORDER BY 1"""
    val asVariant = """SELECT event:card.country::string AS country, count(*) AS high_risk
                       FROM events_variant WHERE event:risk.score::double > 0.8 GROUP BY 1 ORDER BY 1"""
    for ((label, sql) in listOf("text, parsed by every query" to asText, "variant, parsed once" to asVariant)) {
        spark.sql(sql).collectAsList()                                   // warm-up
        val t0 = System.nanoTime()
        val rows = (1..3).map { spark.sql(sql).collectAsList() }.last()
        println("%-28s average of 3: %5.0f ms  %s".format(label, (System.nanoTime() - t0) / 3e6, rows))
    }
    spark.stop()
}
