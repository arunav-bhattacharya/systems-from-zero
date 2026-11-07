package sfz.bigdata.l07

import org.apache.spark.sql.Dataset
import org.apache.spark.sql.catalyst.plans.logical.Filter
import org.apache.spark.sql.catalyst.plans.logical.Join
import org.apache.spark.sql.catalyst.plans.logical.LogicalPlan
import scala.jdk.javaapi.CollectionConverters

/** Reads what Catalyst, Spark's optimizer, did to a query before any row moved. */
object PlanReader {

    /**
     * The short names of the optimizer rules that changed [df]'s plan, sorted: for example
     * `ColumnPruning` and `PushDownPredicates`.
     *
     * `df.queryExecution().optimizedPlan()` makes Spark optimize the plan if it hasn't yet. After
     * that, `df.queryExecution().tracker().rules()` is a Scala map from each rule's full class name
     * to a summary; `numEffectiveInvocations()` counts the runs that changed the plan. Keep the
     * rules from the package `org.apache.spark.sql.catalyst.optimizer` that changed it at least
     * once, and drop the package from the name.
     */
    fun rulesThatFired(df: Dataset<*>): List<String> {
        val qe = df.queryExecution()
        qe.optimizedPlan()                                   // optimization is lazy: run it first
        val prefix = "org.apache.spark.sql.catalyst.optimizer."
        // every rule Spark tried is in the map; "effective" means the rule returned a different tree
        return CollectionConverters.asJava(qe.tracker().rules())
            .filter { (name, summary) -> name.startsWith(prefix) && summary.numEffectiveInvocations() > 0 }
            .keys.map { it.removePrefix(prefix) }
            .sorted()
    }

    /**
     * The conditions of the `Filter` nodes that sit somewhere below a `Join` in [df]'s optimized
     * logical plan, as SQL text (`filter.condition().sql()`), in the order a walk from the root
     * meets them. Empty if the plan has no join.
     *
     * Walk `df.queryExecution().optimizedPlan()` through `children()`. Once the walk has passed a
     * `Join`, every `Filter` it meets counts.
     */
    fun filtersBelowJoins(df: Dataset<*>): List<String> = buildList {
        fun walk(node: LogicalPlan, belowJoin: Boolean) {
            if (belowJoin && node is Filter) add(node.condition().sql())
            // a filter counts only once some join is above it
            val nowBelow = belowJoin || node is Join
            CollectionConverters.asJava(node.children()).forEach { walk(it, nowBelow) }
        }
        walk(df.queryExecution().optimizedPlan(), belowJoin = false)
    }
}
