package sfz.bigdata.l01.demo

import java.sql.Connection

/** Runs one question three ways and prints how many bytes DuckDB actually read for each. */
fun main() {
    PaymentFiles.open().use { c ->
        val csv = PaymentFiles.csv.absolutePath
        val parquet = PaymentFiles.parquet.absolutePath
        println("files: csv ${PaymentFiles.mb(PaymentFiles.csv.length())}, parquet ${PaymentFiles.mb(PaymentFiles.parquet.length())}")
        report(c, "csv, 2 columns    ", "SELECT count(*), sum(amount_cents) FROM read_csv('$csv')")
        // hash(COLUMNS(*)) touches every value of every column, like SELECT * would
        report(c, "parquet, all 10   ", "SELECT sum(hash(COLUMNS(*))) FROM read_parquet('$parquet')")
        report(c, "parquet, 2 columns", "SELECT count(*), sum(amount_cents) FROM read_parquet('$parquet')")
    }
}

/** EXPLAIN ANALYZE runs the query and prints a profile; we keep its timing and "Data Read" lines. */
private fun report(c: Connection, label: String, sql: String) {
    PaymentFiles.bestSeconds(c, sql, times = 1)                       // warm the OS page cache first
    val profile = c.createStatement().use { s ->
        s.executeQuery("EXPLAIN ANALYZE $sql").use { rs -> buildString { while (rs.next()) append(rs.getString(2)) } }
    }
    val read = Regex("""Data Read:\s*([\d.]+ [kMG]?B)""").find(profile)?.groupValues?.get(1) ?: "?"
    val time = Regex("""Total Time:\s*([\d.]+s)""").find(profile)?.groupValues?.get(1) ?: "?"
    println("$label  read $read in $time")
}
