package sfz.batch.l05

import org.apache.parquet.format.Util
import org.apache.spark.sql.functions.col
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import sfz.bigdata.support.Duck
import sfz.bigdata.support.LocalSpark
import sfz.bigdata.support.Plans
import sfz.bigdata.support.TestData
import java.io.ByteArrayInputStream
import java.io.File
import java.io.RandomAccessFile
import java.nio.file.Files

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class ParquetFooterTest {
    private val spark = LocalSpark.session
    private val dir: File = Files.createTempDirectory("l04 parquet").toFile()

    // 400,000 payments written by DuckDB in row groups of about 100,000 rows, once sorted by amount
    // and once in payment_id order (where amounts are random)
    private val sorted = File(dir, "sorted.parquet")
    private val random = File(dir, "random.parquet")
    private val columns = listOf("payment_id", "merchant_id", "card_country", "status", "amount_cents")

    init {
        Duck.connect().use { c ->
            c.createStatement().use { s ->
                s.execute(
                    """
                    CREATE TABLE p AS
                    SELECT i AS payment_id, (hash(i) % 500)::INTEGER AS merchant_id,
                           ['NL','DE','FR','GB'][(hash(i + 1) % 4)::INTEGER + 1] AS card_country,
                           ['AUTHORIZED','CAPTURED','DECLINED','REFUNDED'][(hash(i + 2) % 4)::INTEGER + 1] AS status,
                           (hash(i + 3) % 250000 + 100)::BIGINT AS amount_cents
                    FROM range(400000) t(i)
                    """.trimIndent(),
                )
                s.execute("COPY (SELECT * FROM p ORDER BY amount_cents, payment_id) TO '${sorted.absolutePath}' (FORMAT parquet, ROW_GROUP_SIZE 100000)")
                s.execute("COPY (SELECT * FROM p ORDER BY payment_id) TO '${random.absolutePath}' (FORMAT parquet, ROW_GROUP_SIZE 100000)")
            }
        }
    }

    @AfterAll
    fun cleanUp() {
        dir.deleteRecursively()
    }

    /** DuckDB's own reading of the footer: (row group, column) to (min, max, compressed bytes). */
    private fun duckMetadata(file: File): Map<Pair<Int, String>, Triple<String?, String?, Long>> =
        Duck.connect().use { c ->
            c.createStatement().use { s ->
                s.executeQuery("SELECT row_group_id, path_in_schema, stats_min, stats_max, total_compressed_size FROM parquet_metadata('${file.absolutePath}')").use { rs ->
                    buildMap { while (rs.next()) put(rs.getInt(1) to rs.getString(2), Triple(rs.getString(3), rs.getString(4), rs.getLong(5))) }
                }
            }
        }

    @Test
    fun `footerLength finds the footer from the last 8 bytes`() {
        for (file in listOf(sorted, random)) {
            val length = ParquetFooter.footerLength(file)
            // the footer is the `length` bytes just before the last 8; decode them with Parquet's Thrift classes
            val footer = ByteArray(length)
            RandomAccessFile(file, "r").use { it.seek(file.length() - 8 - length); it.readFully(footer) }
            val metadata = Util.readFileMetaData(ByteArrayInputStream(footer))
            assertThat(metadata.getNum_rows()).isEqualTo(400_000L)
            assertThat(metadata.getRow_groups()).hasSize(4)
            // and the footer sits after every column chunk in the file
            val lastChunkEnd = ParquetFooter.read(file).flatMap { it.columns.values }.maxOf { it.offset + it.bytes }
            assertThat(file.length() - 8 - length).isGreaterThanOrEqualTo(lastChunkEnd)
        }
    }

    @Test
    fun `footerLength rejects a file that is not Parquet`() {
        val csv = File(dir, "payments.csv").apply { writeText("payment_id,amount_cents\n1,1250\n2,990\n") }
        assertThatThrownBy { ParquetFooter.footerLength(csv) }.isInstanceOf(IllegalArgumentException::class.java)
        val tiny = File(dir, "tiny.parquet").apply { writeText("PAR1") }
        assertThatThrownBy { ParquetFooter.footerLength(tiny) }.isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `mayContain keeps a chunk whose range overlaps the filter and skips one that cannot match`() {
        val chunk = ColumnChunk("amount_cents", offset = 4, bytes = 1_000, min = 63_033, max = 125_677)
        assertThat(RowGroupSkipper.mayContain(chunk, 100_000, 110_000)).isTrue()      // inside
        assertThat(RowGroupSkipper.mayContain(chunk, 120_000, 200_000)).isTrue()      // overlaps the top
        assertThat(RowGroupSkipper.mayContain(chunk, 125_677, 125_677)).isTrue()      // touches the max
        assertThat(RowGroupSkipper.mayContain(chunk, 125_678, 250_000)).isFalse()     // all above the max
        assertThat(RowGroupSkipper.mayContain(chunk, 0, 63_032)).isFalse()            // all below the min
    }

    @Test
    fun `a chunk without statistics must always be read`() {
        val noStats = ColumnChunk("created_at", offset = 4, bytes = 1_000, min = null, max = null)
        assertThat(RowGroupSkipper.mayContain(noStats, 0, 1)).isTrue()
    }

    @Test
    fun `on the sorted file a filter on amount reads one row group, on the random file all four`() {
        val big = 240_001L to Long.MAX_VALUE        // WHERE amount_cents > 240000
        assertThat(RowGroupSkipper.rowGroupsToRead(ParquetFooter.read(sorted), "amount_cents", big.first, big.second)).containsExactly(3)
        assertThat(RowGroupSkipper.rowGroupsToRead(ParquetFooter.read(random), "amount_cents", big.first, big.second)).containsExactly(0, 1, 2, 3)
        // DuckDB reads the same footer and must agree on every row group's range
        val duck = duckMetadata(sorted)
        val expected = (0 until 4).filter { g ->
            val (min, max) = duck.getValue(g to "amount_cents")
            max!!.toLong() >= 100_000 && min!!.toLong() <= 130_000
        }
        assertThat(RowGroupSkipper.rowGroupsToRead(ParquetFooter.read(sorted), "amount_cents", 100_000, 130_000)).isEqualTo(expected)
        assertThatThrownBy { RowGroupSkipper.rowGroupsToRead(ParquetFooter.read(sorted), "fraud_score", 0, 1) }
            .isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `bytesToRead counts only the needed columns of the kept row groups`() {
        val groups = ParquetFooter.read(sorted)
        val need = setOf("merchant_id", "amount_cents")
        val duck = duckMetadata(sorted)
        val expected = need.sumOf { duck.getValue(3 to it).third }
        assertThat(RowGroupSkipper.bytesToRead(groups, listOf(3), need)).isEqualTo(expected)
        // every column of every row group adds up to all the data in the file
        val all = RowGroupSkipper.bytesToRead(groups, listOf(0, 1, 2, 3), columns.toSet())
        assertThat(all).isEqualTo(duck.values.sumOf { it.third })
        // two columns of one row group out of four is about a tenth of the file
        assertThat(expected * 5).isLessThan(all)
    }

    @Test
    fun `Spark's scan hands on exactly the rows of the row groups you kept`() {
        for (file in listOf(sorted, random)) {
            val groups = ParquetFooter.read(file)
            val keep = RowGroupSkipper.rowGroupsToRead(groups, "amount_cents", 240_001, Long.MAX_VALUE)
            val query = spark.read().parquet(file.absolutePath)
                .where(col("amount_cents").gt(240_000))
                .select("merchant_id", "amount_cents")
            val matching = query.collectAsList().size
            // the scan skips row groups using the footer; the Filter above it drops single rows
            assertThat(Plans.scanOutputRows(query)).isEqualTo(groups.filter { it.index in keep }.sumOf { it.rows })
            assertThat(matching.toLong()).isLessThan(Plans.scanOutputRows(query))
        }
    }

    @Test
    fun `a file sorted by amount lets a range filter skip most of its row groups`() {
        val payments = TestData.paymentsFrame(spark, TestData.payments(100_000))
        val out = File(dir, "sorted by spark")
        SortedWriter.write(payments, "amount_cents", out.absolutePath, rowGroupBytes = 256 * 1024)
        val files = out.listFiles { f -> f.name.endsWith(".parquet") }!!.toList()
        assertThat(files).hasSize(1)
        val groups = ParquetFooter.read(files.single())
        assertThat(groups.size).isGreaterThanOrEqualTo(4)
        assertThat(groups.sumOf { it.rows }).isEqualTo(100_000L)
        // sorted: every row group's amounts start where the previous one's ended
        groups.zipWithNext { a, b -> assertThat(b.columns.getValue("amount_cents").min!!).isGreaterThanOrEqualTo(a.columns.getValue("amount_cents").max!!) }
        // a narrow range now touches at most two row groups
        val keep = RowGroupSkipper.rowGroupsToRead(groups, "amount_cents", 50_000, 52_000)
        assertThat(keep.size).isBetween(1, 2)
        // merchant_id was not sorted, so its statistics still cover almost everything
        assertThat(RowGroupSkipper.rowGroupsToRead(groups, "merchant_id", 42, 42)).hasSize(groups.size)
    }
}
