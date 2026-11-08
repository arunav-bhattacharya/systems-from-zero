package sfz.batch.l03

import org.apache.spark.sql.Encoders
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.bigdata.support.LocalSpark
import sfz.bigdata.support.TestData

class SparkWordCountTest {
    private val spark = LocalSpark.session
    private val lines = TestData.corpus(20_000)

    @Test
    fun `Spark counts the same words as the hand-made job`() {
        val handMade = MapReduceJob.run(lines.chunked(500), reducers = 4, useCombiner = true).counts()
        val df = SparkWordCount.count(spark.createDataset(lines, Encoders.STRING()))
        assertThat(df.columns()).containsExactly("word", "count")
        val fromSpark = df.collectAsList().associate { it.getString(0) to it.getLong(1).toInt() }
        assertThat(fromSpark).isEqualTo(handMade)
    }

    @Test
    fun `Spark's plan combines on the map side, then shuffles by word`() {
        val df = SparkWordCount.count(spark.createDataset(listOf("approved declined approved"), Encoders.STRING()))
        val plan = df.queryExecution().executedPlan().toString()
        // the combiner survived as a partial aggregate before the exchange
        assertThat(plan).contains("partial_")
        // the shuffle survived as an Exchange that hash-partitions by the key
        assertThat(plan).contains("Exchange hashpartitioning(word")
    }
}
