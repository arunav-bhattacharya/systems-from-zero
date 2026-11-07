package sfz.bigdata.l07

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.sum

/** The nightly settlement job: two reports that both start from the captured payments. */
object NightlyReports {

    /** The rows both reports start from. */
    fun captured(payments: Dataset<Row>): Dataset<Row> = payments.where(col("status").equalTo("CAPTURED"))

    /**
     * Runs both reports and returns their rows: total captured amount per merchant
     * (`merchant_id`, `total_cents`), and the number of captured payments per card country
     * (`card_country`, `count`).
     *
     * Without a cache each report would read the Parquet files again. The team added one, but in
     * the wrong place: it keeps every payment (all four statuses) in memory, and it never lets go,
     * so the next night's run piles another copy on top. Cache only what both reports read, and
     * release it when they are done.
     */
    fun run(payments: Dataset<Row>): Pair<List<Row>, List<Row>> {
        // cache after the filter: memory holds the captured quarter, not the whole table
        val captured = captured(payments).cache()
        try {
            // the first action reads the files once and fills the cache as it goes
            val byMerchant = captured.groupBy("merchant_id").agg(sum("amount_cents").alias("total_cents")).collectAsList()
            // the second action finds the same plan in the cache manager and reads InMemoryTableScan
            val byCountry = captured.groupBy("card_country").count().collectAsList()
            return byMerchant to byCountry
        } finally {
            captured.unpersist()                       // free the executors' memory for the next job
        }
    }
}
