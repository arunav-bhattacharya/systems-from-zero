package sfz.batch.l09

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col

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
        lines.withColumn("amount_minor", col("amount_text").cast("bigint"))
            .withColumn("eur_ppm", col("amount_minor").multiply(col("rate_ppm")))

    /**
     * The lines [parse] could not convert, so someone can look at them: every line whose
     * `amount_minor` or `eur_ppm` is null. Same columns as the input of this function.
     */
    fun rejects(parsed: Dataset<Row>): Dataset<Row> {
        TODO("keep the lines with a null amount_minor or eur_ppm")
    }
}
