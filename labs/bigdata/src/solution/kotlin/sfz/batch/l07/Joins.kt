package sfz.batch.l07

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.broadcast

/** The hourly enrichment job: every payment gets its merchant's name and category. */
object Joins {

    /**
     * Joins [payments] (millions of rows) with [merchants] (500 rows, one per `merchant_id`) on
     * `merchant_id`. Inner join: every payment has a merchant.
     *
     * This version is slow. On the team's cluster Spark can't tell that `merchants` is small (its
     * size estimate is above `spark.sql.autoBroadcastJoinThreshold`), so it plans a sort-merge join:
     * it shuffles every payment by `merchant_id`, sorts both sides and merges them. Make Spark send
     * a copy of `merchants` to every task instead, so the payments never move.
     */
    fun enrich(payments: Dataset<Row>, merchants: Dataset<Row>): Dataset<Row> =
        // the broadcast hint makes merchants the build side whatever its size estimate says:
        // each task builds a hash table from its own copy and streams its payments through it
        payments.join(broadcast(merchants), "merchant_id")
}
