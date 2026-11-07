package sfz.bigdata.l08.demo

import org.apache.spark.api.java.function.FilterFunction
import org.apache.spark.sql.Encoders
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.sum

/** A Java bean, so Encoders.bean can map rows to it: a no-argument constructor and a getter and setter per column. */
class PaymentBean {
    var payment_id: Long = 0
    var merchant_id: Int = 0
    var status: String = ""
    var amount_cents: Long = 0
}

/**
 * One question asked four ways from Kotlin: classic SQL, SQL pipe syntax, the DataFrame API and a
 * typed Dataset with a Kotlin lambda. Prints whether the plans match and what the file scan was
 * asked to filter.
 */
fun main() {
    val spark = demoSpark()
    demoPayments(spark).createOrReplaceTempView("payments")
    val classic = spark.sql(
        """
        SELECT merchant_id, sum(amount_cents) AS total
        FROM payments
        WHERE status = 'CAPTURED'
        GROUP BY merchant_id
        """.trimIndent()
    )
    val pipe = spark.sql(
        """
        FROM payments
        |> WHERE status = 'CAPTURED'
        |> AGGREGATE sum(amount_cents) AS total GROUP BY merchant_id
        """.trimIndent()
    )
    val frame = spark.table("payments").where(col("status").equalTo("CAPTURED"))
        .groupBy("merchant_id").agg(sum("amount_cents").alias("total"))
    val typed = spark.table("payments").`as`(Encoders.bean(PaymentBean::class.java))
        .filter(FilterFunction { it.status == "CAPTURED" })       // Kotlin code: Spark can only call it
        .toDF().groupBy("merchant_id").agg(sum("amount_cents").alias("total"))

    val reference = classic.queryExecution().optimizedPlan()
    for ((label, df) in listOf("classic SQL" to classic, "pipe SQL" to pipe, "DataFrame API" to frame, "typed lambda" to typed)) {
        val same = df.queryExecution().optimizedPlan().sameResult(reference)
        val scan = df.queryExecution().executedPlan().toString().lines().first { "FileScan" in it }
        val pushed = Regex("""PushedFilters: \[([^\]]*)]""").find(scan)!!.groupValues[1]
        val first = df.orderBy("merchant_id").first()
        println("%-14s same plan as classic SQL: %-5s  pushed to Parquet: [%s]  merchant %d total %,d".format(
            label, same, pushed, first.getInt(0), first.getLong(1)))
    }
    println("typed lambda plan, trimmed:")
    typed.queryExecution().executedPlan().toString().lines()
        .filter { "Filter" in it || "DeserializeToObject" in it || "SerializeFromObject" in it }
        .forEach { println("  " + it.trim().replace(Regex("#\\d+L?"), "").take(110)) }
    spark.stop()
}
