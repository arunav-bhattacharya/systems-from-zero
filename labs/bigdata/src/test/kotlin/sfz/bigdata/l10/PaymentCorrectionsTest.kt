package sfz.bigdata.l10

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.io.TempDir
import sfz.bigdata.support.Iceberg
import sfz.bigdata.support.TestData
import java.io.File

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class PaymentCorrectionsTest {
    private lateinit var warehouse: File
    private lateinit var spark: SparkSession

    @BeforeAll
    fun setUp(@TempDir dir: File) {
        warehouse = dir
        spark = Iceberg.session("l10", dir)
    }

    /** A table of 3,000 payments over 3 days: one commit, one data file per day. */
    private fun table(name: String, mode: RowLevelMode, formatVersion: Int = 2): PaymentCorrections {
        val t = PaymentCorrections(spark, "l10.pay.$name")
        t.create(mode, formatVersion)
        Iceberg.payments(spark, 0, 3_000).writeTo(t.name).append()
        return t
    }

    /** Refunds keep the payment and zero its amount, voids remove it, inserts are payments the table never had. */
    private fun corrections(refund: List<Int> = emptyList(), void: List<Int> = emptyList(), insert: List<Int> = emptyList()): Dataset<Row> {
        val all = TestData.payments(5_000, days = 3)
        val rows = refund.map { all[it].copy(status = "REFUNDED", amountCents = 0) } +
            void.map { all[it].copy(status = "VOID") } + insert.map { all[it] }
        return Iceberg.frame(spark, rows)
    }

    private fun dataFiles(name: String) = Iceberg.strings(spark, "SELECT file_path FROM l10.pay.$name.data_files").toSet()

    @Test
    fun `copy-on-write rewrites every data file that holds a corrected row and writes no delete file`() {
        val t = table("cow", RowLevelMode.COPY_ON_WRITE)
        val before = dataFiles("cow")
        val summary = t.applyCorrections(corrections(refund = listOf(30, 31, 32)))     // one payment on each day
        assertThat(summary["deleted-data-files"]).describedAs("old files dropped from the snapshot").isEqualTo("3")
        assertThat(summary["added-data-files"]).isEqualTo("3")
        assertThat(summary["spark.merge-into.num-target-rows-copied"]).describedAs("unchanged rows copied to change 3").isEqualTo("2997")
        assertThat(summary["added-delete-files"] ?: "0").isEqualTo("0")
        assertThat(dataFiles("cow")).doesNotContainAnyElementsOf(before)
        assertThat(spark.sql("SELECT count(*) FROM l10.pay.cow.delete_files").first().getLong(0)).isZero()
    }

    @Test
    fun `merge-on-read on format v2 leaves the data files alone and writes position delete files`() {
        val t = table("mor2", RowLevelMode.MERGE_ON_READ)
        val before = dataFiles("mor2")
        val summary = t.applyCorrections(corrections(refund = listOf(30, 31, 32)))
        assertThat(summary["added-position-delete-files"]).describedAs("one delete file per touched data file").isEqualTo("3")
        assertThat(summary["added-position-deletes"]).describedAs("one (file, position) pair per changed row").isEqualTo("3")
        assertThat(summary["deleted-data-files"]).isNull()
        assertThat(summary["added-records"]).describedAs("the new versions of the 3 rows").isEqualTo("3")
        assertThat(dataFiles("mor2")).containsAll(before)
        val formats = Iceberg.strings(spark, "SELECT file_format FROM l10.pay.mor2.delete_files")
        assertThat(formats).containsExactly("PARQUET", "PARQUET", "PARQUET")
        assertThat(Iceberg.filesOnDisk(File(warehouse, "pay/mor2"), "-deletes.parquet")).hasSize(3)
        assertThat(spark.table(t.name).where("payment_id IN (30, 31, 32)").collectAsList().map { it.getAs<String>("status") to it.getAs<Long>("amount_cents") })
            .describedAs("readers see the corrected rows").containsOnly("REFUNDED" to 0L)
        assertThat(spark.table(t.name).count()).describedAs("and each row once").isEqualTo(3_000)
    }

    @Test
    fun `merge-on-read on format v3 writes one deletion vector per data file, packed in a Puffin file`() {
        val t = table("mor3", RowLevelMode.MERGE_ON_READ, formatVersion = 3)
        val summary = t.applyCorrections(corrections(refund = listOf(30, 31, 32)))
        assertThat(summary["added-dvs"]).describedAs("deletion vectors added").isEqualTo("3")
        val dvs = spark.sql("SELECT file_format, file_path, referenced_data_file FROM l10.pay.mor3.delete_files").collectAsList()
        assertThat(dvs).hasSize(3)
        assertThat(dvs.map { it.getString(0) }.toSet()).containsExactly("PUFFIN")
        // each vector names the one data file it belongs to
        assertThat(dvs.map { it.getString(2).removePrefix("file:") }).allMatch { it in dataFiles("mor3") }.doesNotHaveDuplicates()
        assertThat(dvs.map { it.getString(1) }.toSet()).describedAs("Puffin files written").hasSize(1)
    }

    @Test
    fun `one MERGE refunds, voids and inserts payments in a single commit`() {
        val t = table("merge", RowLevelMode.MERGE_ON_READ)
        val total = spark.table(t.name).agg(org.apache.spark.sql.functions.sum("amount_cents")).first().getLong(0)
        t.applyCorrections(corrections(refund = listOf(1, 2), void = listOf(3, 4, 5), insert = listOf(4_000, 4_001)))
        assertThat(spark.sql("SELECT operation FROM l10.pay.merge.snapshots ORDER BY committed_at").collectAsList().map { it.getString(0) })
            .describedAs("snapshots").containsExactly("append", "overwrite")
        assertThat(spark.table(t.name).count()).isEqualTo(3_000L - 3 + 2)
        assertThat(spark.table(t.name).where("payment_id IN (3, 4, 5)").count()).describedAs("voided").isZero()
        assertThat(spark.table(t.name).where("payment_id IN (1, 2)").collectAsList().map { it.getAs<String>("status") to it.getAs<Long>("amount_cents") })
            .containsOnly("REFUNDED" to 0L)
        assertThat(spark.table(t.name).where("payment_id >= 4000").count()).isEqualTo(2)
        assertThat(spark.table(t.name).where("status = 'VOID'").count()).describedAs("VOID rows are never inserted").isZero()
        val all = TestData.payments(5_000, days = 3)
        val expected = total - (1..5).sumOf { all[it].amountCents } + all[4_000].amountCents + all[4_001].amountCents
        assertThat(spark.table(t.name).agg(org.apache.spark.sql.functions.sum("amount_cents")).first().getLong(0)).isEqualTo(expected)
    }
}
