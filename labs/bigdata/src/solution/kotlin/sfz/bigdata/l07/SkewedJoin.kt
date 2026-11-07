package sfz.bigdata.l07

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.explode
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.pmod
import org.apache.spark.sql.functions.sequence

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
        // big side: each payment gets one salt, deterministic, so the hot merchant splits into `buckets` keys
        val saltedPayments = payments.withColumn("salt", pmod(col("payment_id"), lit(buckets.toLong())))
        // small side: each merchant row is copied once per salt, so every (merchant, salt) key finds its row
        val saltedMerchants = merchants.withColumn("salt", explode(sequence(lit(0L), lit(buckets - 1L))))
        // the shuffle now hashes (merchant_id, salt): merchant 7's payments go to up to `buckets` tasks
        return saltedPayments.join(saltedMerchants, arrayOf("merchant_id", "salt")).drop("salt")
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
    fun aqeSkewSettings(): Map<String, String> = mapOf(
        // skew handling is an AQE rule: it needs the real partition sizes from the map stage
        "spark.sql.adaptive.enabled" to "true",
        "spark.sql.adaptive.skewJoin.enabled" to "true",              // the default, said out loud
        // 256 MB would never trigger on half a megabyte; scale it down with the data
        "spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes" to "100KB",
        // the size each piece of the split partition aims for
        "spark.sql.adaptive.advisoryPartitionSizeInBytes" to "64KB",
    )
}
