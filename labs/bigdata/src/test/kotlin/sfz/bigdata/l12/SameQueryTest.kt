package sfz.bigdata.l12

import org.apache.spark.sql.SparkSession
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.io.TempDir
import sfz.bigdata.support.Duck
import sfz.bigdata.support.LocalSpark
import sfz.bigdata.support.Plans
import sfz.bigdata.support.TestData
import java.io.File

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class SameQueryTest {
    private lateinit var spark: SparkSession
    private lateinit var payments: String
    private lateinit var merchants: String
    private val rows = TestData.payments(20_000)                      // 7 days, 500 merchants

    @BeforeAll
    fun setUp(@TempDir dir: File) {
        spark = LocalSpark.isolated()
        payments = File(dir, "payments").absolutePath
        merchants = File(dir, "merchants").absolutePath
        TestData.paymentsParquet(spark, rows, File(payments), files = 4)
        TestData.merchantsFrame(spark).write().parquet(merchants)
    }

    /** The answer computed in plain Kotlin from the same rows: merchant m has mcc 5000 + m mod 20. */
    private fun expected(): List<DailyVolume> =
        rows.filter { it.status == "CAPTURED" }
            .groupBy { it.dt to 5_000 + it.merchantId % 20 }
            .map { (k, ps) -> DailyVolume(k.first, k.second, ps.size.toLong(), ps.sumOf { it.amountCents }) }
            .sortedWith(compareBy({ it.day }, { it.mcc }))

    @Test
    fun `DuckDB answers from the Parquet files`() {
        val answer = Duck.connect().use { SameQuery.duckdb(it, payments, merchants) }
        assertThat(answer).hasSize(7 * 20)
        assertThat(answer).isEqualTo(expected())
    }

    @Test
    fun `Spark answers the same, and broadcasts the small merchants side`() {
        var answer: List<DailyVolume> = emptyList()
        val plans = Plans.executedDuring(spark) { answer = SameQuery.spark(spark, payments, merchants) }
        assertThat(answer).isEqualTo(expected())
        assertThat(plans.flatMap { Plans.nodes(it) }.map { it.nodeName() }).contains("BroadcastHashJoin")
    }

    @Test
    fun `both engines give exactly the same rows`() {
        val duck = Duck.connect().use { SameQuery.duckdb(it, payments, merchants) }
        assertThat(SameQuery.spark(spark, payments, merchants)).isEqualTo(duck)
    }
}
