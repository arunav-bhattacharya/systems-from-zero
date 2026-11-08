package sfz.batch.l11

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession

/**
 * The payments table as an Apache Iceberg table. [name] has three parts, `catalog.namespace.table`
 * (for example `l11.pay.payments`), and the catalog is an Iceberg catalog that Spark already knows
 * (`spark.sql.catalog.<catalog>` = `org.apache.iceberg.spark.SparkCatalog`).
 */
class PaymentsTable(private val spark: SparkSession, val name: String) {

    /**
     * Creates the table if it doesn't exist: `payment_id BIGINT, merchant_id INT,
     * card_country STRING, currency STRING, amount_cents BIGINT, status STRING,
     * created_at TIMESTAMP`, `USING iceberg`, partitioned by the day of `created_at` with Iceberg's
     * `days(...)` transform. There is no `dt` column: Iceberg derives the day from `created_at`.
     */
    fun create() {
        TODO("CREATE TABLE ... USING iceberg PARTITIONED BY (days(created_at))")
    }

    /**
     * Appends [rows] (the columns above, by name) in one commit, and returns the id of the
     * snapshot that commit created: after it, the table's newest snapshot. The `snapshots`
     * metadata table (`SELECT ... FROM <name>.snapshots`) has `snapshot_id` and `committed_at`.
     */
    fun append(rows: Dataset<Row>): Long {
        TODO("writeTo(name).append(), then read the newest snapshot id from the snapshots metadata table")
    }

    /** The table as it was right after snapshot [snapshotId] was committed (`VERSION AS OF`). */
    fun asOf(snapshotId: Long): Dataset<Row> {
        TODO("time travel with VERSION AS OF")
    }

    /**
     * Two schema changes, as two `ALTER TABLE` statements: rename `amount_cents` to
     * `amount_minor`, and add a nullable `risk_score DOUBLE`. Neither may rewrite a data file.
     */
    fun evolve() {
        TODO("ALTER TABLE ... RENAME COLUMN, then ALTER TABLE ... ADD COLUMN")
    }
}
