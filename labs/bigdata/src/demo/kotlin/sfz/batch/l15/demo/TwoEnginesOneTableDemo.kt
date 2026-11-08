package sfz.batch.l15.demo

import java.io.File

/**
 * One Iceberg table, two engines. Spark creates and appends to the table; DuckDB reads the same
 * files through Iceberg's metadata, with no copy and no Spark. Then Spark appends again and DuckDB
 * sees the new snapshot. DuckDB's Iceberg extension is downloaded once on first use.
 */
fun main() {
    freshDemoDir()
    val spark = demoSpark()
    spark.sql("CREATE TABLE lake.pay.payments (payment_id BIGINT, merchant_id INT, status STRING, amount_cents BIGINT, " +
        "created_at TIMESTAMP) USING iceberg PARTITIONED BY (days(created_at))")
    fun append(from: Long, n: Long) = spark.sql("""
        INSERT INTO lake.pay.payments
        SELECT id, CAST(pmod(hash(id), 500) AS INT), CASE WHEN id % 5 = 0 THEN 'REFUNDED' ELSE 'CAPTURED' END,
               CAST(pmod(hash(id, 2), 250000) + 100 AS BIGINT),
               timestamp_seconds(1793491200 + (id % 3) * 86400 + pmod(hash(id, 4), 86400))
        FROM range($from, ${from + n})""")
    append(0, 1_000_000)
    val table = File(DEMO_DIR, "warehouse/pay/payments").absolutePath
    val question = "SELECT count(*) AS payments, sum(amount_cents) AS amount FROM %s WHERE status = 'CAPTURED'"

    fun sparkSays() = spark.sql(question.format("lake.pay.payments")).first().let { "${it.getLong(0)} payments, ${it.getLong(1)} cents" }
    println("Spark reads:  ${sparkSays()}")
    duck().use { c ->
        c.run("INSTALL iceberg")
        c.run("LOAD iceberg")
        fun duckSays() = c.rows(question.format("iceberg_scan('$table')")).first().let { "${it[0]} payments, ${it[1]} cents" }
        println("DuckDB reads: ${duckSays()}")
        println("DuckDB sees snapshots: " + c.rows("SELECT sequence_number, snapshot_id FROM iceberg_snapshots('$table') ORDER BY 1").map { it[0] })

        append(1_000_000, 500_000)
        println("after Spark appends 500,000 more:")
        println("Spark reads:  ${sparkSays()}")
        println("DuckDB reads: ${duckSays()}")
        println("DuckDB sees snapshots: " + c.rows("SELECT sequence_number, snapshot_id FROM iceberg_snapshots('$table') ORDER BY 1").map { it[0] })
    }
    spark.stop()
}
