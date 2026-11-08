package sfz.batch.l15

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.col
import org.apache.spark.sql.functions.count
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.functions.sum
import java.sql.Connection

data class DailyVolume(val day: String, val mcc: Int, val payments: Long, val amountCents: Long)

object SameQuery {

    fun duckdb(connection: Connection, paymentsDir: String, merchantsDir: String): List<DailyVolume> {
        // DuckDB reads the Parquet files in place: no load step, no cluster, one process
        val sql = """
            SELECT p.dt, m.mcc, count(*) AS payments, sum(p.amount_cents) AS amount_cents
            FROM read_parquet('$paymentsDir/*.parquet') p
            JOIN read_parquet('$merchantsDir/*.parquet') m ON p.merchant_id = m.merchant_id
            WHERE p.status = 'CAPTURED'
            GROUP BY p.dt, m.mcc
            ORDER BY p.dt, m.mcc
        """.trimIndent()
        return connection.createStatement().use { s ->
            s.executeQuery(sql).use { rs ->
                buildList {
                    while (rs.next()) add(DailyVolume(rs.getString(1), rs.getInt(2), rs.getLong(3), rs.getLong(4)))
                }
            }
        }
    }

    fun spark(spark: SparkSession, paymentsDir: String, merchantsDir: String): List<DailyVolume> {
        val payments = spark.read().parquet(paymentsDir)
        val merchants = spark.read().parquet(merchantsDir)
        // the same plan in DataFrame form; the small merchants side is broadcast (lesson 7)
        return payments.where(col("status").equalTo(lit("CAPTURED")))
            .join(merchants, "merchant_id")
            .groupBy("dt", "mcc")
            .agg(count(lit(1)).alias("payments"), sum("amount_cents").alias("amount_cents"))
            .orderBy("dt", "mcc")
            .collectAsList()
            .map { DailyVolume(it.getString(0), it.getInt(1), it.getLong(2), it.getLong(3)) }
    }
}
