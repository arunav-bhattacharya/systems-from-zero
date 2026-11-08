package sfz.batch.l12

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession

/**
 * How an Iceberg table applies a row-level change (MERGE, UPDATE, DELETE) to data files that can
 * never be edited. [property] is the value of the table properties `write.merge.mode`,
 * `write.update.mode` and `write.delete.mode`.
 */
enum class RowLevelMode(val property: String) {
    /** Rewrite every data file that holds a changed row. Writes are slow, reads stay simple. */
    COPY_ON_WRITE("copy-on-write"),

    /** Leave data files alone and write delete files (or deletion vectors) instead. Readers merge them. */
    MERGE_ON_READ("merge-on-read"),
}

/**
 * The payments table as an Iceberg table that takes corrections. [name] has three parts,
 * `catalog.namespace.table`, for example `l12.pay.cow`.
 */
class PaymentCorrections(private val spark: SparkSession, val name: String) {

    /**
     * Creates the table: `payment_id BIGINT, merchant_id INT, card_country STRING, currency STRING,
     * amount_cents BIGINT, status STRING, created_at TIMESTAMP`, `USING iceberg`, partitioned by
     * `days(created_at)`. Set the table properties `format-version` to [formatVersion] and all
     * three of `write.merge.mode`, `write.update.mode` and `write.delete.mode` to [mode]'s
     * property value.
     */
    fun create(mode: RowLevelMode, formatVersion: Int = 2) {
        TODO("CREATE TABLE ... USING iceberg PARTITIONED BY (days(created_at)) TBLPROPERTIES (...)")
    }

    /**
     * Applies a batch of [corrections] in ONE `MERGE INTO` and returns the summary of the snapshot
     * it committed (the `summary` map of the newest row of `<name>.snapshots`).
     *
     * [corrections] has the table's columns. Match on `payment_id`:
     * - matched, and the correction's `status` is `VOID`: delete the payment;
     * - matched otherwise: set the payment's `status` and `amount_cents` to the correction's;
     * - not matched, and the status is not `VOID`: insert the correction as a new payment.
     */
    fun applyCorrections(corrections: Dataset<Row>): Map<String, String> {
        TODO("register corrections as a temp view, MERGE INTO $name USING it, then read the newest snapshot's summary")
    }
}
