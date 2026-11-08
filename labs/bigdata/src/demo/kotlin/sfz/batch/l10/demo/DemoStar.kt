package sfz.batch.l10.demo

import java.io.File
import java.sql.Connection
import java.sql.DriverManager

/** Everything the lesson 10 demos write goes under build/l10. */
val DEMO_DIR = File("build/l10")

/** A new in-memory DuckDB database. */
fun duck(): Connection = DriverManager.getConnection("jdbc:duckdb:")

fun Connection.run(sql: String) {
    createStatement().use { it.execute(sql) }
}

fun Connection.rows(sql: String): List<List<Any?>> = createStatement().use { s ->
    s.executeQuery(sql).use { rs ->
        buildList { while (rs.next()) add((1..rs.metaData.columnCount).map { rs.getObject(it) }) }
    }
}

/** The best of [runs] timings of [block], in milliseconds, and its last result. */
fun <T> best(runs: Int = 5, block: () -> T): Pair<T, Double> {
    var result: T? = null
    val ms = (1..runs).minOf {
        val t0 = System.nanoTime()
        result = block()
        (System.nanoTime() - t0) / 1e6
    }
    @Suppress("UNCHECKED_CAST")
    return (result as T) to ms
}

/**
 * The operational tables, the way the services keep them: [n] payments over the 7 days from
 * Sunday 2026-11-01, 500 merchants, and the merchant category lookup. Same rows every run.
 */
fun rawTables(c: Connection, n: Long) {
    c.run("""
        CREATE TABLE raw_payments AS
        SELECT i AS payment_id,
               CAST(hash(i) % 500 AS INTEGER) AS merchant_id,
               ['NL', 'DE', 'FR', 'GB', 'US', 'IN', 'BR', 'JP'][CAST(hash(i + 1) % 8 AS INTEGER) + 1] AS card_country,
               ['EUR', 'USD', 'GBP', 'INR'][CAST(hash(i + 2) % 4 AS INTEGER) + 1] AS currency,
               CAST(hash(i + 3) % 250000 + 100 AS BIGINT) AS amount_cents,
               ['AUTHORIZED', 'CAPTURED', 'CAPTURED', 'DECLINED', 'REFUNDED'][CAST(hash(i + 4) % 5 AS INTEGER) + 1] AS status,
               TIMESTAMP '2026-11-01 00:00:00' + to_days(CAST(i % 7 AS INTEGER)) + to_seconds(CAST(hash(i + 5) % 86400 AS BIGINT)) AS created_at
        FROM range($n) t(i)""")
    c.run("""
        CREATE TABLE raw_merchants AS
        SELECT CAST(m AS INTEGER) AS merchant_id, 'Merchant ' || m AS merchant_name, CAST(5000 + m % 20 AS INTEGER) AS mcc,
               CASE WHEN m % 10 = 0 THEN 'HIGH' WHEN m % 3 = 0 THEN 'MEDIUM' ELSE 'LOW' END AS risk_tier,
               ['NL', 'DE', 'FR', 'GB'][CAST(m % 4 AS INTEGER) + 1] AS country
        FROM range(500) t(m)""")
    c.run("""
        CREATE TABLE raw_mcc AS
        SELECT CAST(5000 + k AS INTEGER) AS mcc, ['Groceries', 'Travel', 'Electronics', 'Gaming'][CAST(k // 5 AS INTEGER) + 1] AS category
        FROM range(20) t(k)""")
}

/**
 * A star built from the raw tables: `dim_date`, `dim_merchant` (one version per merchant, valid
 * from 2026-11-01) and `fact_payment`, loaded day by day, so it is stored in date order.
 */
fun buildStar(c: Connection) {
    c.run("""
        CREATE TABLE dim_date AS
        SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key, d AS day, dayname(d) AS day_name,
               dayofweek(d) IN (0, 6) AS is_weekend, month(d) AS month, quarter(d) AS quarter
        FROM (SELECT CAST(DATE '2026-11-01' + CAST(i AS INTEGER) AS DATE) AS d FROM range(7) t(i))""")
    c.run("""
        CREATE TABLE dim_merchant AS
        SELECT CAST(row_number() OVER (ORDER BY m.merchant_id) AS INTEGER) AS merchant_key, m.merchant_id, m.merchant_name,
               m.mcc, c.category, m.risk_tier, m.country,
               DATE '2026-11-01' AS valid_from, DATE '9999-12-31' AS valid_to, true AS is_current
        FROM raw_merchants m JOIN raw_mcc c ON c.mcc = m.mcc""")
    c.run("""
        CREATE TABLE fact_payment AS
        SELECT p.payment_id, CAST(strftime(p.created_at, '%Y%m%d') AS INTEGER) AS date_key, m.merchant_key,
               p.card_country, p.currency, p.status, p.amount_cents
        FROM raw_payments p JOIN dim_merchant m ON m.merchant_id = p.merchant_id
        ORDER BY date_key, payment_id""")
}

/** The size of every file under [dir], in MB. */
fun megabytes(dir: File): Double = dir.walkTopDown().filter { it.isFile }.sumOf { it.length() } / 1e6
