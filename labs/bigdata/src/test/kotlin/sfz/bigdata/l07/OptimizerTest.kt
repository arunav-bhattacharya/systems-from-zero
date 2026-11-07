package sfz.bigdata.l07

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.catalyst.plans.logical.Filter
import org.apache.spark.sql.catalyst.plans.logical.Join
import org.apache.spark.sql.catalyst.plans.logical.LogicalPlan
import org.apache.spark.sql.functions.col
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import sfz.bigdata.support.LocalSpark
import sfz.bigdata.support.TestData
import scala.jdk.javaapi.CollectionConverters
import java.io.File
import java.nio.file.Files

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class OptimizerTest {
    private val spark: SparkSession = LocalSpark.isolated()
    private val dir: File = Files.createTempDirectory("l07 optimizer").toFile()
    private val payments: Dataset<Row> = TestData.paymentsParquet(spark, TestData.payments(2_000), File(dir, "payments"))
    private val merchants: Dataset<Row> = TestData.merchantsFrame(spark)

    // written the way people think: join first, then keep Dutch cards at grocery merchants
    private val query: Dataset<Row> = payments.join(merchants, "merchant_id")
        .where(col("card_country").equalTo("NL").and(col("mcc").equalTo(5_001)))
        .select("payment_id", "merchant_name", "amount_cents")

    private fun kids(p: LogicalPlan): List<LogicalPlan> = CollectionConverters.asJava(p.children())
    private fun firstFilter(p: LogicalPlan): Filter? = p as? Filter ?: kids(p).firstNotNullOfOrNull { firstFilter(it) }
    private fun hasJoin(p: LogicalPlan): Boolean = p is Join || kids(p).any { hasJoin(it) }

    @AfterAll
    fun cleanUp() {
        dir.deleteRecursively()
    }

    @Test
    fun `as written, the filter sits above the join`() {
        // the analyzed plan is your code, checked but not rewritten: Filter on top, Join below it
        val analyzed = query.queryExecution().analyzed()
        val filter = firstFilter(analyzed)
        assertThat(filter).describedAs("a Filter in the analyzed plan").isNotNull
        assertThat(hasJoin(filter!!)).describedAs("the Join sits below that Filter").isTrue()
        // and nothing below the join is filtered yet; your walk must agree with that on this plan
        assertThat(PlanReader.filtersBelowJoins(payments.where(col("card_country").equalTo("NL")))).isEmpty()
    }

    @Test
    fun `the optimizer moves each half of the filter below the join, to the side it belongs to`() {
        val below = PlanReader.filtersBelowJoins(query)
        assertThat(below).describedAs("filters below the join").hasSize(2)
        // the card country lives in payments, so that half went down the payments side, with a null check added
        assertThat(below).anySatisfy { assertThat(it).contains("card_country").contains("'NL'").contains("IS NOT NULL") }
        // the mcc lives in merchants, so the other half went down the merchants side
        assertThat(below).anySatisfy { assertThat(it).contains("5001") }
        assertThat(below).noneSatisfy { assertThat(it).contains("card_country").contains("5001") }
    }

    @Test
    fun `rulesThatFired names the rewrites that changed the plan`() {
        val rules = PlanReader.rulesThatFired(query)
        assertThat(rules).contains("PushDownPredicates", "ColumnPruning", "InferFiltersFromConstraints")
        assertThat(rules).isSorted()
        // analyzer rules resolve names; they don't optimize, so they are not in the list
        assertThat(rules).noneSatisfy { assertThat(it).startsWith("Resolve") }
        // a query with nothing to push or prune changes much less
        val simple = PlanReader.rulesThatFired(payments.select("payment_id"))
        assertThat(simple).doesNotContain("PushDownPredicates", "InferFiltersFromConstraints")
    }
}
