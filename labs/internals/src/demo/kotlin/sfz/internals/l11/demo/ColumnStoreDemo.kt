package sfz.internals.l11.demo

import java.nio.file.Files
import java.sql.DriverManager
import java.sql.Statement

/**
 * Loads the same 1,000,000 payments as the lesson's PostgreSQL Try its into DuckDB, a column store that runs
 * inside this JVM, and prints what its storage did with them:
 *
 * 1. the size of the database file after CHECKPOINT (compare it with PostgreSQL's heap for the same rows),
 * 2. the encoding DuckDB chose for each column (it tries several per segment and keeps the smallest),
 * 3. the zone map (min and max) it keeps for created_at in each row group of 122,880 rows,
 * 4. how many row groups a one-day query scans, with the rows in insertion order and shuffled.
 *
 * The database is a temporary file, deleted at the end. The first run downloads the DuckDB driver (about 80 MB).
 */
fun main() {
    val dir = Files.createTempDirectory("sfz-duckdb")
    val file = dir.resolve("payments.duckdb")
    try {
        DriverManager.getConnection("jdbc:duckdb:$file").use { conn ->
            conn.createStatement().use { st -> run(st, file) }
        }
    } finally {
        dir.toFile().deleteRecursively()
    }
}

private fun run(st: Statement, file: java.nio.file.Path) {
    st.execute("SET threads = 1")
    st.execute(
        """
        CREATE TABLE payments AS
        SELECT g AS id,
               1 + (g * 7919) % 10000 AS merchant_id,
               (['EUR', 'EUR', 'EUR', 'GBP', 'USD', 'SEK'])[1 + (g * 31) % 6] AS currency,
               CASE WHEN g % 50 = 0 THEN 'refunded' WHEN g % 20 = 0 THEN 'failed' ELSE 'settled' END AS status,
               (g * 104729) % 100000 AS amount_cents,
               TIMESTAMP '2026-10-01' + INTERVAL (g * 2) SECOND AS created_at
        FROM range(1, 1000001) t(g)
        """.trimIndent(),
    )
    st.execute("CHECKPOINT")
    val version = st.executeQuery("SELECT version()").use { it.next(); it.getString(1) }
    println("DuckDB %s: 1,000,000 payments, database file %.1f MB after CHECKPOINT".format(version, Files.size(file) / 1e6))

    println()
    println("%-14s %-12s %s".format("column", "encoding", "row groups"))
    st.executeQuery(
        """
        SELECT column_name, string_agg(DISTINCT compression, ', ') AS encodings, count(DISTINCT row_group_id) AS row_groups
        FROM pragma_storage_info('payments')
        WHERE segment_type <> 'VALIDITY'
        GROUP BY column_name, column_id ORDER BY column_id
        """.trimIndent(),
    ).use { rs -> while (rs.next()) println("%-14s %-12s %d".format(rs.getString(1), rs.getString(2), rs.getLong(3))) }

    println()
    println("zone map of created_at, first 3 row groups:")
    st.executeQuery(
        """
        SELECT row_group_id, count, stats.min::VARCHAR AS min, stats.max::VARCHAR AS max
        FROM pragma_storage_info('payments')
        WHERE column_name = 'created_at' AND segment_type <> 'VALIDITY'
        ORDER BY row_group_id LIMIT 3
        """.trimIndent(),
    ).use { rs ->
        while (rs.next()) println("  row group %d: %,d rows, min %s, max %s".format(rs.getLong(1), rs.getLong(2), rs.getString(3), rs.getString(4)))
    }

    val oneDay = "WHERE created_at >= TIMESTAMP '2026-10-15' AND created_at < TIMESTAMP '2026-10-16'"
    println()
    println("SELECT count(*), sum(amount_cents) FROM ... $oneDay")
    println("  in insertion order: " + scanned(st, "SELECT count(*), sum(amount_cents) FROM payments $oneDay"))
    st.execute("CREATE TABLE shuffled AS SELECT * FROM payments ORDER BY hash(id)")
    st.execute("CHECKPOINT")
    println("  shuffled:           " + scanned(st, "SELECT count(*), sum(amount_cents) FROM shuffled $oneDay"))
}

/** Runs EXPLAIN ANALYZE and pulls the scan's "Row Groups Scanned" line and the rows it returned. */
private fun scanned(st: Statement, sql: String): String {
    val plan = st.executeQuery("EXPLAIN ANALYZE $sql").use { rs -> rs.next(); rs.getString(2) }
    val lines = plan.lines().map { it.trim('│', ' ') }
    val groups = lines.first { it.startsWith("Row Groups Scanned") }
    val scan = lines.indexOfFirst { "Table Scan" in it }
    val rows = lines.drop(scan).first { it.matches(Regex("""[\d,]+ rows.*""")) }.substringBefore(" rows")
    return "$groups, $rows rows matched"
}
