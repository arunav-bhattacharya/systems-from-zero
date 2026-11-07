package sfz.bigdata.l08

import org.apache.spark.SparkThrowable
import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.RowFactory
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.types.DataTypes
import org.apache.spark.sql.types.StructType
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.catchThrowable
import org.junit.jupiter.api.Test
import sfz.bigdata.support.LocalSpark

class AnsiTest {
    private val spark: SparkSession = LocalSpark.isolated()                 // Spark 4 defaults: ANSI on
    private val legacy: SparkSession = LocalSpark.isolated("spark.sql.ansi.enabled" to "false")

    private val schema = StructType()
        .add("line_no", DataTypes.IntegerType, false)
        .add("amount_text", DataTypes.StringType, false)
        .add("rate_ppm", DataTypes.LongType, false)

    private fun lines(s: SparkSession): Dataset<Row> = s.createDataFrame(listOf(
        RowFactory.create(1, "1250", 920_000L),             // 12.50 USD at 0.92
        RowFactory.create(2, "12,50", 920_000L),            // a decimal comma: not a whole number
        RowFactory.create(3, " 300 ", 1_000_000L),          // spaces: a cast trims them, so this one is fine
        RowFactory.create(4, "", 1_000_000L),               // empty
        RowFactory.create(5, "9000000000000", 1_085_000L),  // 9 x 10^12 x 1.085 x 10^6 overflows a BIGINT
        RowFactory.create(6, "4000000000000", 1_085_000L),  // 4.34 x 10^18 still fits
    ), schema).repartition(2)                               // a real shuffle, so the casts run in tasks

    private fun byLine(df: Dataset<Row>) =
        df.orderBy("line_no").collectAsList().associate { it.getInt(0) to (it.get(3) as Long? to it.get(4) as Long?) }

    @Test
    fun `ANSI mode is on, and parse keeps every line instead of failing the job`() {
        assertThat(spark.conf().get("spark.sql.ansi.enabled")).isEqualTo("true")
        val thrown = catchThrowable { SettlementLines.parse(lines(spark)).collectAsList() }
        assertThat(thrown).describedAs("parse threw under ANSI mode: %s", thrown?.message?.lines()?.firstOrNull()).isNull()
        assertThat(SettlementLines.parse(lines(spark)).count()).isEqualTo(6)
    }

    @Test
    fun `parse converts the good lines and leaves null where a value can't be converted`() {
        val out = byLine(SettlementLines.parse(lines(spark)))
        assertThat(out[1]).isEqualTo(1_250L to 1_150_000_000L)
        assertThat(out[2]).isEqualTo(null to null)
        assertThat(out[3]).isEqualTo(300L to 300_000_000L)
        assertThat(out[4]).isEqualTo(null to null)
        assertThat(out[5]).describedAs("the overflowing line").isEqualTo(9_000_000_000_000L to null)
        assertThat(out[6]).isEqualTo(4_000_000_000_000L to 4_340_000_000_000_000_000L)
    }

    @Test
    fun `the old code is not safe with ANSI off either, it just fails silently`() {
        // what Spark 3 did with the same expression: no error, a wrapped-around negative number
        val old = legacy.sql("SELECT CAST('9000000000000' AS BIGINT) * 1085000").first().getLong(0)
        assertThat(old).isNegative()
        // under ANSI the same expression stops with an error class you can search for
        val thrown = catchThrowable { spark.sql("SELECT CAST('9000000000000' AS BIGINT) * 1085000").collectAsList() }
        assertThat((thrown as SparkThrowable).condition).isEqualTo("ARITHMETIC_OVERFLOW")
        // and yours gives null on that line, which rejects() then reports
        val rejected = SettlementLines.rejects(SettlementLines.parse(lines(spark))).select("line_no").collectAsList().map { it.getInt(0) }
        assertThat(rejected).containsExactlyInAnyOrder(2, 4, 5)
    }

    @Test
    fun `rejects keeps the columns it was given`() {
        val parsed = SettlementLines.parse(lines(spark))
        assertThat(SettlementLines.rejects(parsed).columns()).containsExactly(*parsed.columns())
        assertThat(SettlementLines.rejects(parsed.where(col("line_no").equalTo(1))).count()).isZero()
    }
}
