package sfz.bigdata.support

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.execution.QueryExecution
import org.apache.spark.sql.util.QueryExecutionListener
import java.util.concurrent.CopyOnWriteArrayList
import org.apache.spark.sql.execution.SparkPlan
import org.apache.spark.sql.execution.adaptive.AdaptiveSparkPlanExec
import org.apache.spark.sql.execution.adaptive.QueryStageExec
import org.apache.spark.util.AccumulatorV2
import scala.jdk.javaapi.CollectionConverters

/** Helpers for looking inside Spark's physical plans and their run-time metrics. */
object Plans {
    /**
     * Every node of [plan], root first. Looks inside the wrappers that adaptive query execution
     * adds (`AdaptiveSparkPlan`, `ShuffleQueryStage`, ...), so it works with AQE on or off.
     */
    fun nodes(plan: SparkPlan): List<SparkPlan> = buildList {
        fun walk(p: SparkPlan) {
            add(p)
            when (p) {
                is AdaptiveSparkPlanExec -> walk(p.executedPlan())
                is QueryStageExec -> walk(p.plan())
                else -> CollectionConverters.asJava(p.children()).forEach(::walk)
            }
        }
        walk(plan)
    }

    /** The nodes of [df]'s physical plan. After an action has run, this is the plan that ran. */
    fun nodes(df: Dataset<*>): List<SparkPlan> = nodes(df.queryExecution().executedPlan())

    /** The current value of the metric [name] (for example `numOutputRows`) of [node]. */
    fun metric(node: SparkPlan, name: String): Long {
        val m = CollectionConverters.asJava(node.metrics())[name] ?: error("${node.nodeName()} has no metric '$name'")
        // SQLMetric.value() is overloaded for Kotlin (Long and the erased Any); go through AccumulatorV2
        return ((m as AccumulatorV2<*, *>).value() as Number).toLong()
    }

    /**
     * How many rows the file scan of [df] handed to the operators above it, after an action has
     * run. A Parquet scan hands on every row of every row group it could not skip; the `Filter`
     * above it then drops the rows that don't match.
     */
    fun scanOutputRows(df: Dataset<*>): Long =
        nodes(df).filter { it.nodeName().startsWith("Scan") }
            .ifEmpty { error("no file scan in the plan of this query") }
            .sumOf { metric(it, "numOutputRows") }

    /** The node names of [df]'s plan, root first: `HashAggregate`, `Exchange`, `SortMergeJoin`, ... */
    fun names(df: Dataset<*>): List<String> = nodes(df).map { it.nodeName() }

    /**
     * Runs [block] and returns the physical plan of every action it ran on [spark], in order, as it
     * ran (after adaptive re-planning). Use it to look at the plans of code that runs its own
     * actions, such as a report that calls `collectAsList()` twice.
     */
    fun executedDuring(spark: SparkSession, block: () -> Unit): List<SparkPlan> {
        val plans = CopyOnWriteArrayList<SparkPlan>()
        val listener = object : QueryExecutionListener {
            override fun onSuccess(funcName: String, qe: QueryExecution, durationNs: Long) {
                plans += qe.executedPlan()
            }

            override fun onFailure(funcName: String, qe: QueryExecution, exception: Exception) {}
        }
        val bus = spark.sparkContext().listenerBus()
        bus.waitUntilEmpty()
        spark.listenerManager().register(listener)
        try {
            block()
            bus.waitUntilEmpty()
        } finally {
            spark.listenerManager().unregister(listener)
        }
        return plans.toList()
    }
}
