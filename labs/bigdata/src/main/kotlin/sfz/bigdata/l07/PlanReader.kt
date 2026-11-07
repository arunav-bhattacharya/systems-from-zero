package sfz.bigdata.l07

import org.apache.spark.sql.Dataset

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
        TODO("read the planning tracker and keep the optimizer rules that changed the plan")
    }

    /**
     * The conditions of the `Filter` nodes that sit somewhere below a `Join` in [df]'s optimized
     * logical plan, as SQL text (`filter.condition().sql()`), in the order a walk from the root
     * meets them. Empty if the plan has no join.
     *
     * Walk `df.queryExecution().optimizedPlan()` through `children()`. Once the walk has passed a
     * `Join`, every `Filter` it meets counts.
     */
    fun filtersBelowJoins(df: Dataset<*>): List<String> {
        TODO("walk the optimized logical plan and collect the filters under a join")
    }
}
