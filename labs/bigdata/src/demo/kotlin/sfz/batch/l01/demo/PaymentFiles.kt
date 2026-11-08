package sfz.batch.l01.demo

import java.io.File
import java.sql.Connection
import java.sql.DriverManager

/**
 * Ten million made-up card payments, written once as CSV and as Parquet under build/l01.
 * DuckDB generates them from `range`, so every run on every machine gets the same rows.
 */
object PaymentFiles {
    const val ROWS = 10_000_000L
    private val dir = File("build/l01")
    val csv = File(dir, "payments.csv")
    val parquet = File(dir, "payments.parquet")

    private val generator = """
        SELECT i                                                                   AS payment_id,
               TIMESTAMP '2026-10-01' + to_seconds((hash(i) % 2592000)::BIGINT)    AS created_at,
               (hash(i + 1) % 5000)::INTEGER                                       AS merchant_id,
               ['NL','DE','FR','GB','US','IN','BR','JP'][(hash(i + 2) % 8)::INTEGER + 1] AS card_country,
               ['EUR','USD','GBP','INR'][(hash(i + 3) % 4)::INTEGER + 1]           AS currency,
               (100 + hash(i + 4) % 250000)::BIGINT                                AS amount_cents,
               ['AUTHORIZED','CAPTURED','DECLINED','REFUNDED'][(hash(i + 5) % 4)::INTEGER + 1] AS status,
               (5000 + hash(i + 6) % 900)::INTEGER                                 AS mcc,
               round((hash(i + 7) % 10000) / 10000.0, 4)                           AS fraud_score,
               md5(i::VARCHAR)[1:16]                                               AS idempotency_key
        FROM range($ROWS) t(i)
    """.trimIndent()

    /** An in-memory DuckDB with the two files in place (written on the first call only). */
    fun open(): Connection {
        val c = DriverManager.getConnection("jdbc:duckdb:")
        if (!csv.exists() || !parquet.exists()) {
            dir.mkdirs()
            println("Writing %,d payments to %s (first run only, about 10 s)...".format(ROWS, dir.path))
            c.createStatement().use { s ->
                s.execute("COPY ($generator) TO '${parquet.absolutePath}' (FORMAT parquet)")
                s.execute("COPY (FROM read_parquet('${parquet.absolutePath}')) TO '${csv.absolutePath}' (HEADER)")
            }
        }
        return c
    }

    /** Megabytes, the decimal way disks count them. */
    fun mb(bytes: Long) = "%,.0f MB".format(bytes / 1e6)

    /** Runs [sql] [times] times and returns the fastest run in seconds (the first run warms caches). */
    fun bestSeconds(c: Connection, sql: String, times: Int = 3): Double =
        (1..times).minOf {
            val t0 = System.nanoTime()
            c.createStatement().use { s -> s.executeQuery(sql).use { rs -> while (rs.next()) Unit } }
            (System.nanoTime() - t0) / 1e9
        }
}
