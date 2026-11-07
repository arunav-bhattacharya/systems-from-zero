package sfz.bigdata.support

import java.sql.Connection
import java.sql.DriverManager

/** Small helpers for DuckDB over JDBC. Each call to [connect] opens a fresh in-memory database. */
object Duck {
    fun connect(): Connection = DriverManager.getConnection("jdbc:duckdb:")

    /** Runs [sql] and returns the first column of the first row as a Long (null if SQL NULL). */
    fun Connection.longOf(sql: String): Long? = createStatement().use { s ->
        s.executeQuery(sql).use { rs ->
            check(rs.next()) { "query returned no rows: $sql" }
            rs.getLong(1).takeUnless { rs.wasNull() }
        }
    }

    /** The text DuckDB prints for `EXPLAIN [sql]`: the plan it would run, without running it. */
    fun Connection.explain(sql: String): String = createStatement().use { s ->
        s.executeQuery("EXPLAIN $sql").use { rs ->
            buildString { while (rs.next()) appendLine(rs.getString(2)) }
        }
    }

    /**
     * How many files a Parquet scan in [sql] will open, and how many it found, read from the
     * `Scanning Files: 2/6` line of DuckDB's plan. Null if the plan has no such line.
     */
    fun Connection.filesScanned(sql: String): Pair<Int, Int>? =
        Regex("""Scanning Files:\s*(\d+)\s*/\s*(\d+)""").find(explain(sql))
            ?.destructured?.let { (read, total) -> read.toInt() to total.toInt() }
}
