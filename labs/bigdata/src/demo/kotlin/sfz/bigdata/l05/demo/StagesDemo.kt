package sfz.bigdata.l05.demo

import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.sum

/**
 * Runs the settlement report (captured payments, total per merchant) and prints its plan and what
 * the scheduler ran: first with adaptive query execution (AQE) off, then on.
 * Pass `-Pargs=ui` to keep the Spark UI open at http://localhost:4040 until you press Enter.
 */
fun main(args: Array<String>) {
    val ui = "ui" in args
    val spark = demoSpark("local[4]", ui = ui)
    val payments = demoPayments(spark)
    val log = JobLog(spark)
    for (aqe in listOf(false, true)) {
        spark.conf().set("spark.sql.adaptive.enabled", aqe.toString())
        val report = payments.where(col("status").equalTo("CAPTURED"))
            .groupBy("merchant_id").agg(sum("amount_cents").alias("total_cents"))
        if (!aqe) {
            println(report.queryExecution().executedPlan().toString().lines()
                .joinToString("\n") { it.replace(Regex("""Location: .*?, PartitionFilters"""), "PartitionFilters") })
        }
        log.clear()
        report.collectAsList()
        println("AQE %-5s %s".format(if (aqe) "on:" else "off:", log.summary()))
    }
    if (ui) {
        println("Spark UI: ${spark.sparkContext().uiWebUrl().get()}  (press Enter to stop)")
        readlnOrNull()
    }
    spark.stop()
}
