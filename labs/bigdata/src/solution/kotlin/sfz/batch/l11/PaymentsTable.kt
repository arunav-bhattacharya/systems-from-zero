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
        // hidden partitioning: the partition value is computed from created_at, and queries never name it
        spark.sql(
            """
            CREATE TABLE IF NOT EXISTS $name (
                payment_id BIGINT, merchant_id INT, card_country STRING, currency STRING,
                amount_cents BIGINT, status STRING, created_at TIMESTAMP)
            USING iceberg
            PARTITIONED BY (days(created_at))
            """.trimIndent()
        )
    }

    /**
     * Appends [rows] (the columns above, by name) in one commit, and returns the id of the
     * snapshot that commit created: after it, the table's newest snapshot. The `snapshots`
     * metadata table (`SELECT ... FROM <name>.snapshots`) has `snapshot_id` and `committed_at`.
     */
    fun append(rows: Dataset<Row>): Long {
        // one write, one commit: new data files, new manifest, new manifest list, new metadata.json, pointer swap
        rows.writeTo(name).append()
        return spark.sql("SELECT snapshot_id FROM $name.snapshots ORDER BY committed_at DESC LIMIT 1").first().getLong(0)
    }

    /** The table as it was right after snapshot [snapshotId] was committed (`VERSION AS OF`). */
    fun asOf(snapshotId: Long): Dataset<Row> =
        // reads that snapshot's manifest list, so it sees exactly the files that snapshot listed
        spark.sql("SELECT * FROM $name VERSION AS OF $snapshotId")

    /**
     * Two schema changes, as two `ALTER TABLE` statements: rename `amount_cents` to
     * `amount_minor`, and add a nullable `risk_score DOUBLE`. Neither may rewrite a data file.
     */
    fun evolve() {
        // the column keeps its field id, so old files (which store ids, not just names) still match it
        spark.sql("ALTER TABLE $name RENAME COLUMN amount_cents TO amount_minor")
        // a new id; old files don't have it, so readers fill in null
        spark.sql("ALTER TABLE $name ADD COLUMN risk_score DOUBLE")
    }
}
