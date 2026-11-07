package sfz.bigdata.l12.demo

import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.count
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.sum
import java.io.File

/**
 * Ten million payments as Parquet, and one question asked of two engines on this laptop: per day
 * and merchant category, how many captured payments and how much money? Times DuckDB and Spark
 * (local[*], every core) and checks that the answers match.
 */
fun main() {
    freshDemoDir()
    val payments = File(DEMO_DIR, "payments")
    val merchants = File(DEMO_DIR, "merchants")
    val c = duck()
    writePayments(c, 10_000_000, payments, merchants)
    println("payments: 10,000,000 rows in ${payments.list()!!.size} Parquet files, %.0f MB".format(megabytes(payments)))

    fun timed(runs: Int, block: () -> List<List<Any?>>): Pair<List<List<Any?>>, List<Long>> {
        var result: List<List<Any?>> = emptyList()
        val times = (1..runs).map {
            val t0 = System.nanoTime()
            result = block()
            (System.nanoTime() - t0) / 1_000_000
        }
        return result to times
    }

    val (duckAnswer, duckTimes) = timed(3) {
        c.rows("""
            SELECT p.dt::VARCHAR, m.mcc, count(*), sum(p.amount_cents)
            FROM read_parquet('${payments.absolutePath}/*.parquet') p
            JOIN read_parquet('${merchants.absolutePath}/*.parquet') m ON p.merchant_id = m.merchant_id
            WHERE p.status = 'CAPTURED'
            GROUP BY ALL
            ORDER BY 1, 2""")
    }
    println("DuckDB: ${duckTimes.joinToString(", ") { "$it ms" }}")

    val t0 = System.nanoTime()
    val spark = demoSpark()
    val startup = (System.nanoTime() - t0) / 1_000_000
    val (sparkAnswer, sparkTimes) = timed(3) {
        spark.read().parquet(payments.absolutePath).where(col("status").equalTo(lit("CAPTURED")))
            .join(spark.read().parquet(merchants.absolutePath), "merchant_id")
            .groupBy(col("dt").cast("string").alias("day"), col("mcc"))
            .agg(count(lit(1)), sum("amount_cents"))
            .orderBy("day", "mcc")
            .collectAsList()
            .map { r -> (0 until 4).map { r.get(it) } }
    }
    println("Spark:  ${sparkTimes.joinToString(", ") { "$it ms" }} (plus $startup ms to start the session)")

    val same = duckAnswer.map { it.map(Any?::toString) } == sparkAnswer.map { it.map(Any?::toString) }
    println("answers: ${duckAnswer.size} rows each, identical: $same")
    println("first row: ${duckAnswer.first()}")
    println("best run, Spark / DuckDB: about %.0fx".format(sparkTimes.min().toDouble() / duckTimes.min()))
    spark.stop()
    c.close()
}
