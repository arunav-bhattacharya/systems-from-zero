package sfz.batch.l11

import org.apache.iceberg.expressions.Expressions
import org.apache.iceberg.spark.Spark3Util
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.sum
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.io.TempDir
import java.io.File

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class PaymentsTableTest {
    // one warehouse for the whole class: a JUnit temp folder, deleted after the last test
    private lateinit var warehouse: File
    private lateinit var spark: SparkSession

    @BeforeAll
    fun setUp(@TempDir dir: File) {
        warehouse = dir
        spark = icebergSession(dir)
    }

    private fun table(name: String) = PaymentsTable(spark, "l11.pay.$name")
    private fun dir(name: String) = File(warehouse, "pay/$name")

    @Test
    fun `create writes the first metadata file, partitioned by the day of created_at, with no snapshot yet`() {
        table("created").create()
        val meta = File(dir("created"), "metadata")
        assertThat(File(meta, "version-hint.text").readText().trim()).isEqualTo("1")
        val v1 = json(File(meta, "v1.metadata.json"))
        assertThat(v1.path("current-snapshot-id").asLong()).describedAs("no data yet").isEqualTo(-1L)
        val spec = v1.path("partition-specs").first().path("fields")
        assertThat(spec).hasSize(1)
        assertThat(spec.first().path("transform").asText()).isEqualTo("day")
        assertThat(spec.first().path("source-id").asInt()).isEqualTo(fieldId(v1, "created_at"))
        assertThat(fieldId(v1, "dt")).describedAs("a dt column").isEqualTo(-1)
    }

    @Test
    fun `every append is one commit, a new metadata file whose pointer names the new snapshot`() {
        val t = table("appends")
        t.create()
        val first = t.append(batch(spark, 0, 300))
        val second = t.append(batch(spark, 300, 200))
        val meta = File(dir("appends"), "metadata")
        assertThat(File(meta, "version-hint.text").readText().trim()).isEqualTo("3")
        val v3 = json(File(meta, "v3.metadata.json"))
        assertThat(v3.path("current-snapshot-id").asLong()).isEqualTo(second)
        val snapshots = v3.path("snapshots").toList()
        assertThat(snapshots.map { it.path("snapshot-id").asLong() }).containsExactly(first, second)
        assertThat(snapshots[1].path("parent-snapshot-id").asLong()).describedAs("the second commit's parent").isEqualTo(first)
        assertThat(snapshots[0].path("summary").path("added-records").asText()).isEqualTo("300")
        // the old metadata file is never edited: v2 still says the first snapshot is current
        assertThat(json(File(meta, "v2.metadata.json")).path("current-snapshot-id").asLong()).isEqualTo(first)
    }

    @Test
    fun `asOf reads the table as it was after the first commit`() {
        val t = table("travel")
        t.create()
        val first = t.append(batch(spark, 0, 300))
        t.append(batch(spark, 300, 200))
        assertThat(spark.table(t.name).count()).isEqualTo(500)
        assertThat(t.asOf(first).count()).isEqualTo(300)
        assertThat(t.asOf(first).agg(sum("payment_id")).first().getLong(0)).isEqualTo((0L until 300L).sum())
    }

    @Test
    fun `evolve renames and adds a column without rewriting any data file`() {
        val t = table("evolve")
        t.create()
        val first = t.append(batch(spark, 0, 300))
        val before = dataFilesOnDisk(dir("evolve"))
        val amountId = fieldId(json(currentMetadata(dir("evolve"))), "amount_cents")
        val total = spark.table(t.name).agg(sum("amount_cents")).first().getLong(0)

        t.evolve()

        assertThat(dataFilesOnDisk(dir("evolve"))).describedAs("data files after evolve").isEqualTo(before)
        val now = json(currentMetadata(dir("evolve")))
        assertThat(fieldId(now, "amount_minor")).describedAs("the renamed column keeps its id").isEqualTo(amountId)
        assertThat(fieldId(now, "amount_cents")).isEqualTo(-1)
        assertThat(fieldId(now, "risk_score")).isEqualTo(now.path("last-column-id").asInt())
        // old files are read through the ids: the values come back under the new name, and the new column is null
        assertThat(spark.table(t.name).agg(sum("amount_minor")).first().getLong(0)).isEqualTo(total)
        assertThat(spark.table(t.name).where(col("risk_score").isNotNull()).count()).isZero()
        // a snapshot from before the rename still reads, with the schema it had
        assertThat(t.asOf(first).columns()).contains("amount_cents")
    }

    @Test
    fun `hidden partitioning lets a filter on created_at skip the other days' files`() {
        val t = table("hidden")
        t.create()
        t.append(batch(spark, 0, 300))                         // 3 days
        val iceberg = Spark3Util.loadIcebergTable(spark, t.name)
        val all = iceberg.newScan().planFiles().use { it.count() }
        // a filter on the raw column; nobody mentions a partition column
        val oneDay = iceberg.newScan().filter(
            Expressions.and(
                Expressions.greaterThanOrEqual("created_at", "2026-11-02T00:00:00+00:00"),
                Expressions.lessThan("created_at", "2026-11-03T00:00:00+00:00"),
            )
        ).planFiles().use { it.count() }
        assertThat(all).isGreaterThanOrEqualTo(3)
        assertThat(oneDay).isPositive().isLessThan(all)
        assertThat(spark.table(t.name).where("created_at >= '2026-11-02' AND created_at < '2026-11-03'").count()).isEqualTo(100)
    }
}
