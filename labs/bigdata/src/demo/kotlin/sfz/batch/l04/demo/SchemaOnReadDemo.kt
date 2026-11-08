package sfz.batch.l04.demo

import java.io.File
import java.sql.Connection
import java.sql.DriverManager

/**
 * A "table" that is only a directory of files plus a schema. Adding a file adds rows, and a bad
 * file is only noticed when a query reads it.
 */
fun main() {
    val dir = File("build/l03/raw/payments").apply { deleteRecursively(); mkdirs() }
    DriverManager.getConnection("jdbc:duckdb:").use { c ->
        // two batches land as files; nobody runs INSERT
        batch(c, File(dir, "batch-1.parquet"), from = 0)
        batch(c, File(dir, "batch-2.parquet"), from = 1_000)
        c.run("CREATE VIEW payments AS SELECT * FROM read_parquet('${dir.absolutePath}/*.parquet')")
        println("2 files:  " + c.query("SELECT count(*), sum(amount_cents) FROM payments"))

        batch(c, File(dir, "batch-3.parquet"), from = 2_000)
        println("3 files:  " + c.query("SELECT count(*), sum(amount_cents) FROM payments"))

        // an upstream job changes amount_cents to text like '12.50 EUR'; writing the file works fine
        c.run("COPY (SELECT 3000 AS payment_id, '12.50 EUR' AS amount_cents) TO '${File(dir, "batch-4.parquet").absolutePath}' (FORMAT parquet)")
        println("4 files:  " + runCatching { c.query("SELECT count(*), sum(amount_cents) FROM payments") }
            .getOrElse { "query failed: " + it.message!!.lineSequence().first() })
    }
}

private fun batch(c: Connection, file: File, from: Int) =
    c.run("COPY (SELECT i AS payment_id, (i % 997) * 100 AS amount_cents FROM range($from, ${from + 1_000}) t(i)) TO '${file.absolutePath}' (FORMAT parquet)")

private fun Connection.run(sql: String) = createStatement().use { it.execute(sql) }

private fun Connection.query(sql: String): String = createStatement().use { s ->
    s.executeQuery(sql).use { rs -> rs.next(); (1..rs.metaData.columnCount).joinToString(", ") { "${rs.metaData.getColumnLabel(it)} = ${rs.getString(it)}" } }
}
