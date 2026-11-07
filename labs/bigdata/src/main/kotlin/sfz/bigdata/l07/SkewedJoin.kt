package sfz.bigdata.l07

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row

/**
 * Joins payments with their merchants when one merchant, a marketplace, has 30% of all payments.
 * Hash partitioning sends every row of that merchant to the same reduce task, so one task does
 * most of the join while the others wait.
 */
object SkewedJoin {

    /** The plain join, as the team wrote it. Leave it as it is: the tests compare against it. */
    fun plain(payments: Dataset<Row>, merchants: Dataset<Row>): Dataset<Row> =
        payments.join(merchants, "merchant_id")

    /**
     * The same rows as [plain] (the payment columns plus `merchant_name` and `mcc`, and no extra
     * column), with each merchant's payments spread over [buckets] join keys instead of one.
     *
     * Salt both sides. Give every payment a salt from 0 until [buckets], computed from its
     * `payment_id` so that a retried task computes the same salt (no `rand()`). Give every merchant
     * [buckets] copies of its row, one per salt. Join on `merchant_id` and the salt, then drop the
     * salt.
     */
    fun salted(payments: Dataset<Row>, merchants: Dataset<Row>, buckets: Int): Dataset<Row> {
        TODO("add a salt to both sides and join on (merchant_id, salt)")
    }

    /**
     * The SQL settings that make adaptive query execution split the hot merchant's partition when
     * [plain] runs on the tests' data: 40,000 payments, so the hot partition is about half a
     * megabyte. The tests start from a session where AQE is off and broadcasting is off, then apply
     * these settings.
     *
     * Spark only treats a partition as skewed if it is more than 5 times the median partition AND
     * bigger than `spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes` (256 MB by default).
     * Each piece of a split partition aims at `spark.sql.adaptive.advisoryPartitionSizeInBytes`.
     * Sizes are strings such as "64KB".
     */
    fun aqeSkewSettings(): Map<String, String> {
        TODO("turn AQE on and scale its skew thresholds down to test-sized data")
    }
}
