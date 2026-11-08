package sfz.batch.l03.demo

import org.apache.spark.sql.Encoders
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.explode
import org.apache.spark.sql.functions.split

/** The same three-line word count in Spark, with the physical plan Spark chose for it. */
fun main() {
    val spark = demoSpark()
    val lines = spark.createDataset(
        listOf("approved declined approved", "approved refunded approved", "declined approved refunded"),
        Encoders.STRING(),
    )
    val counts = lines
        .select(explode(split(col("value"), " ")).alias("word"))   // map: one row per word
        .groupBy("word")                                           // shuffle by word
        .count()                                                   // reduce (and combine)
    counts.explain()
    counts.orderBy("word").show()
    spark.stop()
}
