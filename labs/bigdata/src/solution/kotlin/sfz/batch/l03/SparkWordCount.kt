package sfz.batch.l03

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.explode
import org.apache.spark.sql.functions.lower
import org.apache.spark.sql.functions.split

object SparkWordCount {
    fun count(lines: Dataset<String>): Dataset<Row> =
        lines
            // map side: one row per word, the same rule as WordCount.map
            .select(explode(split(lower(col("value")), "[^a-z]+")).alias("word"))
            .where(col("word").notEqual(""))
            // groupBy + count is map, combine, shuffle and reduce in one line: Spark counts partially
            // per partition, shuffles the partial counts by word, then adds them up
            .groupBy("word")
            .count()
}
