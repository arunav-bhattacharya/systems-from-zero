package sfz.bigdata.l06.demo

import org.apache.spark.sql.functions.sum

/**
 * The same groupBy over 1,000,000 payments with spark.sql.shuffle.partitions set to 4, 200 and
 * 2,000 (AQE off), and then 2,000 with AQE on. Prints the tasks each run needed and its time.
 */
fun main() {
    val spark = demoSpark()
    val log = StageLog(spark)
    val p = payments(spark).cache()
    p.count()                                                     // read once into memory, so runs compare the shuffle only
    for ((partitions, aqe) in listOf(4 to false, 200 to false, 2000 to false, 2000 to true)) {
        spark.conf().set("spark.sql.shuffle.partitions", partitions.toString())
        spark.conf().set("spark.sql.adaptive.enabled", aqe.toString())
        // a new DataFrame for every run: running the same one again would reuse its shuffle files
        fun totals() = p.groupBy("merchant_id").agg(sum("amount_cents"))
        totals().collectAsList()                                  // warm-up
        val times = (1..3).map {
            val df = totals()
            val t0 = System.nanoTime()
            df.collectAsList()
            (System.nanoTime() - t0) / 1e6
        }
        val (_, stages) = log.run { totals().collectAsList() }
        println("shuffle.partitions=%-5d AQE %-3s -> tasks per stage %-10s shuffled %,d rows (%,d bytes), best of 3: %4.0f ms".format(
            partitions, if (aqe) "on" else "off", stages.map { it.tasks }, stages.sumOf { it.recordsWritten },
            stages.sumOf { it.bytesWritten }, times.min()))
    }
    spark.stop()
}
