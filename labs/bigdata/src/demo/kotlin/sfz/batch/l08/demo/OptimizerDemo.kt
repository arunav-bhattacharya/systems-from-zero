package sfz.batch.l08.demo

import scala.jdk.javaapi.CollectionConverters

/**
 * One SQL query through Catalyst's four plans, and the optimizer rules that changed it. Nothing
 * runs: explain() only plans.
 */
fun main() {
    val spark = demoSpark()
    demoPayments(spark).createOrReplaceTempView("payments")
    demoMerchants(spark).createOrReplaceTempView("merchants")
    val df = spark.sql(
        """
        SELECT m.merchant_name, p.amount_cents
        FROM payments p JOIN merchants m ON p.merchant_id = m.merchant_id
        WHERE p.card_country = 'NL' AND m.mcc = 5001 AND p.amount_cents > 100 * 1000
        """.trimIndent()
    )
    val qe = df.queryExecution()
    println("== 1. parsed: your words, nothing looked up yet ==")
    println(clean(qe.logical()))
    println("== 2. analyzed: names resolved against the catalog ==")
    println(clean(qe.analyzed()))
    println("== 3. optimized: rewritten by rules ==")
    println(clean(qe.optimizedPlan()))
    println("== 4. physical: the operators that will run ==")
    println(clean(qe.executedPlan()))
    val prefix = "org.apache.spark.sql.catalyst.optimizer."
    val fired = CollectionConverters.asJava(qe.tracker().rules())
        .filter { (name, s) -> name.startsWith(prefix) && s.numEffectiveInvocations() > 0 }
        .keys.map { it.removePrefix(prefix) }.sorted()
    val tried = CollectionConverters.asJava(qe.tracker().rules()).keys.count { it.startsWith(prefix) }
    println("optimizer rules tried: $tried, rules that changed the plan: ${fired.size}")
    fired.forEach { println("  $it") }
    spark.stop()
}
