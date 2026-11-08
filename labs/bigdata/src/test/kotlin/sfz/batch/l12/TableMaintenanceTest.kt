package sfz.batch.l12

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.sum
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.io.TempDir
import sfz.bigdata.support.Iceberg
import sfz.bigdata.support.TestData
import java.io.File

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class TableMaintenanceTest {
    private lateinit var warehouse: File
    private lateinit var spark: SparkSession

    @BeforeAll
    fun setUp(@TempDir dir: File) {
        warehouse = dir
        spark = Iceberg.session("l12", dir)
    }

    /**
     * A merge-on-read table built the way a stream builds one: three small appends of 300
     * payments (3 days each, so 9 small data files), then one MERGE that refunds a payment on each
     * day (3 more small data files and 3 position delete files). Built with plain SQL, so these
     * tests don't depend on your PaymentCorrections.
     */
    private fun messyTable(name: String): String {
        val t = "l12.ops.$name"
        spark.sql("CREATE TABLE $t (payment_id BIGINT, merchant_id INT, card_country STRING, currency STRING, amount_cents BIGINT, " +
            "status STRING, created_at TIMESTAMP) USING iceberg PARTITIONED BY (days(created_at)) " +
            "TBLPROPERTIES ('write.merge.mode' = 'merge-on-read')")
        repeat(3) { b -> Iceberg.payments(spark, b * 300, 300).writeTo(t).append() }
        Iceberg.frame(spark, TestData.payments(3, days = 3).map { it.copy(status = "REFUNDED", amountCents = 0) }).createOrReplaceTempView("l12_fix_$name")
        spark.sql("MERGE INTO $t t USING l12_fix_$name c ON t.payment_id = c.payment_id " +
            "WHEN MATCHED THEN UPDATE SET t.status = c.status, t.amount_cents = c.amount_cents")
        return t
    }

    private fun totals(t: String) = spark.table(t).count() to spark.table(t).agg(sum("amount_cents")).first().getLong(0)

    @Test
    fun `health counts snapshots, data files, delete files and small files from the metadata`() {
        val t = messyTable("health")
        val m = TableMaintenance(spark, t)
        assertThat(m.health()).isEqualTo(TableHealth(snapshots = 4, dataFiles = 12, deleteFiles = 3, smallDataFiles = 12))
        assertThat(m.health(smallFileBytes = 1).smallDataFiles).describedAs("no file is under 1 byte").isZero()
    }

    @Test
    fun `compact rewrites the small files into one per day and applies the deletes`() {
        val t = messyTable("compact")
        val m = TableMaintenance(spark, t)
        val before = totals(t)
        val result = m.compact()
        assertThat(result.rewrittenDataFiles).isEqualTo(12)
        assertThat(result.addedDataFiles).describedAs("one file per day").isEqualTo(3)
        assertThat(result.removedDeleteFiles).describedAs("deletes applied, then dropped").isEqualTo(3)
        // two commits: the rewrite itself ("replace"), then the removal of the dangling delete files
        assertThat(m.health()).isEqualTo(TableHealth(snapshots = 6, dataFiles = 3, deleteFiles = 0, smallDataFiles = 3))
        assertThat(totals(t)).describedAs("same rows, same amounts").isEqualTo(before)
        assertThat(spark.sql("SELECT operation FROM $t.snapshots ORDER BY committed_at").collectAsList().map { it.getString(0) })
            .describedAs("snapshot operations").startsWith("append", "append", "append", "overwrite", "replace")
    }

    @Test
    fun `expiring snapshots deletes the files only old snapshots used and ends time travel to them`() {
        val t = messyTable("expire")
        val m = TableMaintenance(spark, t)
        val first = spark.sql("SELECT snapshot_id FROM $t.snapshots ORDER BY committed_at LIMIT 1").first().getLong(0)
        m.compact()
        val dir = File(warehouse, "ops/expire")
        assertThat(Iceberg.filesOnDisk(dir)).describedAs("old files stay on disk after compaction").hasSize(12 + 3 + 3)
        assertThat(spark.sql("SELECT count(*) FROM $t VERSION AS OF $first").first().getLong(0)).isEqualTo(300)

        val deleted = m.expireSnapshots(retainLast = 1)

        assertThat(deleted).describedAs("data files deleted").isEqualTo(12)
        assertThat(m.health().snapshots).isEqualTo(1)
        val live = Iceberg.strings(spark, "SELECT file_path FROM $t.data_files").toSet()
        assertThat(Iceberg.filesOnDisk(dir)).describedAs("data and delete files left on disk").isEqualTo(live)
        assertThatThrownBy { spark.sql("SELECT count(*) FROM $t VERSION AS OF $first").collect() }
            .describedAs("time travel to an expired snapshot")
        assertThat(totals(t).first).isEqualTo(900)
    }
}
