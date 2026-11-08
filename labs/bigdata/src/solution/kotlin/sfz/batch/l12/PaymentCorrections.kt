package sfz.batch.l12

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession

enum class RowLevelMode(val property: String) {
    COPY_ON_WRITE("copy-on-write"),
    MERGE_ON_READ("merge-on-read"),
}

class PaymentCorrections(private val spark: SparkSession, val name: String) {

    fun create(mode: RowLevelMode, formatVersion: Int = 2) {
        // the three modes are separate properties: MERGE, UPDATE and DELETE can each choose
        spark.sql(
            """
            CREATE TABLE $name (
                payment_id BIGINT, merchant_id INT, card_country STRING, currency STRING,
                amount_cents BIGINT, status STRING, created_at TIMESTAMP)
            USING iceberg
            PARTITIONED BY (days(created_at))
            TBLPROPERTIES (
                'format-version' = '$formatVersion',
                'write.merge.mode' = '${mode.property}',
                'write.update.mode' = '${mode.property}',
                'write.delete.mode' = '${mode.property}')
            """.trimIndent()
        )
    }

    fun applyCorrections(corrections: Dataset<Row>): Map<String, String> {
        val view = "l12_corrections_" + name.replace('.', '_')
        corrections.createOrReplaceTempView(view)
        // one statement, one commit: Spark joins the corrections to the table to find the rows
        // (and the files) they touch, then rewrites those files or writes delete files
        spark.sql(
            """
            MERGE INTO $name t
            USING $view c
            ON t.payment_id = c.payment_id
            WHEN MATCHED AND c.status = 'VOID' THEN DELETE
            WHEN MATCHED THEN UPDATE SET t.status = c.status, t.amount_cents = c.amount_cents
            WHEN NOT MATCHED AND c.status <> 'VOID' THEN INSERT *
            """.trimIndent()
        )
        // the commit's own record of what it did: files added and removed, deletes written
        return spark.sql("SELECT summary FROM $name.snapshots ORDER BY committed_at DESC LIMIT 1")
            .first().getJavaMap<String, String>(0).toMap()
    }
}
