package sfz.batch.l11

import org.apache.spark.sql.SparkSession
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.io.TempDir
import java.io.File

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class MetadataWalkTest {
    // one warehouse for the whole class: a JUnit temp folder, deleted after the last test
    private lateinit var warehouse: File
    private lateinit var spark: SparkSession

    @BeforeAll
    fun setUp(@TempDir dir: File) {
        warehouse = dir
        spark = icebergSession(dir)
    }

    /** A table built with plain SQL, so these tests don't depend on your PaymentsTable. */
    private fun table(name: String, batches: Int): File {
        spark.sql("CREATE TABLE l11.walk.$name (payment_id BIGINT, merchant_id INT, card_country STRING, currency STRING, " +
            "amount_cents BIGINT, status STRING, created_at TIMESTAMP) USING iceberg PARTITIONED BY (days(created_at))")
        repeat(batches) { b -> batch(spark, b * 200, 200).writeTo("l11.walk.$name").append() }
        return File(warehouse, "walk/$name")
    }

    @Test
    fun `currentMetadataFile follows version-hint text to the newest metadata file`() {
        val dir = table("hint", batches = 2)
        val file = MetadataWalk.currentMetadataFile(dir)
        assertThat(file.name).isEqualTo("v3.metadata.json")              // create, then two commits
        assertThat(file).exists()
    }

    @Test
    fun `currentSnapshot reads the current id and its manifest list from the JSON`() {
        val empty = table("empty", batches = 0)
        assertThat(MetadataWalk.currentSnapshot(MetadataWalk.currentMetadataFile(empty))).describedAs("a table with no commit").isNull()
        val dir = table("snap", batches = 2)
        val snap = MetadataWalk.currentSnapshot(MetadataWalk.currentMetadataFile(dir))!!
        val newest = spark.sql("SELECT snapshot_id, manifest_list FROM l11.walk.snap.snapshots ORDER BY committed_at DESC LIMIT 1").first()
        assertThat(snap.id).isEqualTo(newest.getLong(0))
        assertThat(snap.manifestList).isEqualTo(newest.getString(1))
        assertThat(File(snap.manifestList.removePrefix("file:"))).exists()
    }

    @Test
    fun `dataFiles walks the manifest list and the manifests to the same files Spark reads`() {
        val dir = table("files", batches = 3)
        val snap = MetadataWalk.currentSnapshot(MetadataWalk.currentMetadataFile(dir))!!
        val mine = MetadataWalk.dataFiles(snap.manifestList)
        val spark = spark.sql("SELECT file_path FROM l11.walk.files.files").collectAsList().map { it.getString(0).removePrefix("file:") }
        assertThat(mine).isSorted().containsExactlyInAnyOrderElementsOf(spark)
        assertThat(mine).hasSize(dataFilesOnDisk(dir).size)
        // an older snapshot lists fewer files: the first commit's manifest list knows only its own
        val first = this.spark.sql("SELECT manifest_list FROM l11.walk.files.snapshots ORDER BY committed_at LIMIT 1").first().getString(0)
        assertThat(MetadataWalk.dataFiles(first)).hasSizeLessThan(mine.size).isSubsetOf(mine)
    }
}
