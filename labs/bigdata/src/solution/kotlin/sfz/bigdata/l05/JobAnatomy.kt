package sfz.bigdata.l05

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.execution.SparkPlan
import org.apache.spark.sql.execution.exchange.ShuffleExchangeExec
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.sum
import scala.jdk.javaapi.CollectionConverters

/**
 * Reading stages out of a real physical plan (`df.queryExecution().executedPlan()`), with adaptive
 * query execution switched off, so the plan is a plain tree of operators.
 */
object JobAnatomy {

    /**
     * Every shuffle in [plan]: the `ShuffleExchangeExec` nodes, which `explain()` prints as
     * `Exchange`. Visit the root, then its `children()` (a Scala `Seq`: turn it into a Java list with
     * `scala.jdk.javaapi.CollectionConverters.asJava`), and so on down. Root first.
     */
    fun shuffles(plan: SparkPlan): List<ShuffleExchangeExec> {
        val here = if (plan is ShuffleExchangeExec) listOf(plan) else emptyList()
        return here + CollectionConverters.asJava(plan.children()).flatMap { shuffles(it) }
    }

    /** How many stages one job of [plan] runs: each shuffle is a stage boundary. */
    fun stageCount(plan: SparkPlan): Int {
        // n cuts make n + 1 pieces (for a single-input plan)
        return shuffles(plan).size + 1
    }

    /**
     * How many tasks one job of [plan] runs, for a plan with a single input of [inputPartitions]
     * partitions: one task per partition in every stage. A shuffle's partition count is
     * `numPartitions()`.
     */
    fun taskCount(plan: SparkPlan, inputPartitions: Int): Int {
        return inputPartitions + shuffles(plan).sumOf { it.numPartitions() }
    }
}

/** The settlement report that finance asks for every night. */
object SettlementReport {

    /**
     * The total of `amount_cents` per merchant over the payments whose `status` is `CAPTURED`:
     * two columns, `merchant_id` and `total_cents`, one row per merchant.
     *
     * Only describe the work. Call no action (`count`, `collect`, `show`, `write`): Spark should run
     * nothing until the caller asks for the result.
     */
    fun build(payments: Dataset<Row>): Dataset<Row> {
        // transformations only: this builds a plan and returns at once
        return payments
            .where(col("status").equalTo("CAPTURED"))     // narrow: stays in the first stage
            .groupBy("merchant_id")                        // wide: a shuffle by merchant_id
            .agg(sum("amount_cents").alias("total_cents"))
    }
}
