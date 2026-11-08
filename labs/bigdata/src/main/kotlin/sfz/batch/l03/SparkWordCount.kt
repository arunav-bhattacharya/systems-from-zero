package sfz.batch.l03

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row

/** The same word count, written for Spark with the DataFrame API. */
object SparkWordCount {
    /**
     * Counts words in [lines] (one column named `value`, one line per row) with the same rules as
     * [WordCount.map]: lowercase, split on anything that is not a to z, ignore empty strings.
     *
     * Returns one row per distinct word with two columns, `word` (string) and `count` (long).
     * Let Spark do the work: no `collect()` and no Kotlin loops over the data.
     */
    fun count(lines: Dataset<String>): Dataset<Row> {
        TODO("functions.split + explode + filter + groupBy(\"word\").count()")
    }
}
