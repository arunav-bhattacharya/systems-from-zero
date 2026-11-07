package sfz.bigdata.l08

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.try_multiply

/**
 * Reads a card network's settlement file. Each line has `line_no` (INT), `amount_text` (the amount
 * in minor units, as text, exactly as the network wrote it) and `rate_ppm` (BIGINT: what one minor
 * unit of the line's currency is worth in euro cents, in millionths: 920,000 means 0.92).
 */
object SettlementLines {

    /**
     * Adds `amount_minor` (BIGINT, the amount as a number) and `eur_ppm` (BIGINT,
     * `amount_minor * rate_ppm`: the euro value in millionths of a cent, exact, rounded later).
     *
     * This is the Spark 3 code, and it ran for years. With ANSI mode on, the default since Spark
     * 4.0, one malformed amount or one product too big for a BIGINT now fails the whole job. Keep
     * every line instead: a line whose amount isn't a whole number, or whose product overflows,
     * gets null in that column, and the job goes on.
     */
    fun parse(lines: Dataset<Row>): Dataset<Row> =
        // try_cast: '12,50' or '' becomes null instead of failing the task (CAST_INVALID_INPUT)
        lines.withColumn("amount_minor", col("amount_text").try_cast("bigint"))
            // try_multiply: a product past 9.2 x 10^18 becomes null instead of ARITHMETIC_OVERFLOW
            // (with ANSI off it would have wrapped around to a negative number, silently)
            .withColumn("eur_ppm", try_multiply(col("amount_minor"), col("rate_ppm")))

    /**
     * The lines [parse] could not convert, so someone can look at them: every line whose
     * `amount_minor` or `eur_ppm` is null. Same columns as the input of this function.
     */
    fun rejects(parsed: Dataset<Row>): Dataset<Row> =
        // a null here always means "could not convert": the input columns are never null
        parsed.where(col("amount_minor").isNull().or(col("eur_ppm").isNull()))
}
