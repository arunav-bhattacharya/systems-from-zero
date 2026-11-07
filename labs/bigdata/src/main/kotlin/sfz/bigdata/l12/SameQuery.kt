package sfz.bigdata.l12

import org.apache.spark.sql.SparkSession
import java.sql.Connection

/** One row of the answer: a day, a merchant category, and its captured payments. */
data class DailyVolume(val day: String, val mcc: Int, val payments: Long, val amountCents: Long)

/**
 * The same question, answered by two engines over the same Parquet files: per day (`dt`) and
 * merchant category (`mcc`), how many CAPTURED payments, and their total `amount_cents`?
 *
 * The payments files have the columns of the track's test data (`payment_id`, `merchant_id`,
 * `status`, `amount_cents`, `dt` as a yyyy-MM-dd string, ...). The merchants files have
 * `merchant_id`, `merchant_name` and `mcc`. Join them on `merchant_id`. Sort the answer by day,
 * then mcc.
 */
object SameQuery {

    /** The answer from DuckDB, reading every `.parquet` file in the two folders with `read_parquet`. */
    fun duckdb(connection: Connection, paymentsDir: String, merchantsDir: String): List<DailyVolume> {
        TODO("one SQL statement over read_parquet('...'), then map each row to a DailyVolume")
    }

    /** The answer from Spark, reading the same folders with `spark.read().parquet(...)`. */
    fun spark(spark: SparkSession, paymentsDir: String, merchantsDir: String): List<DailyVolume> {
        TODO("read both folders, filter, join, group, aggregate, sort, collect")
    }
}
