package sfz.bigdata.l03.demo

import org.apache.spark.sql.SaveMode
import java.io.File
import java.sql.DriverManager

/**
 * Spark writes a week of payments as a Hive-style table, one directory per day.
 * Then DuckDB plans two queries for the same day and says how many files each would open.
 */
fun main() {
    val lake = File("build/l03/lake")
    val spark = demoSpark()
    demoPayments(spark).write().mode(SaveMode.Overwrite).partitionBy("dt").parquet(lake.absolutePath)
    spark.stop()

    val files = dataFiles(lake)
    println("%d files in %d directories, for example:".format(files.size, lake.listFiles { f -> f.isDirectory }!!.size))
    files.take(3).forEach { println("  $it") }

    val scan = "read_parquet('${lake.absolutePath}/**/*.parquet', hive_partitioning = true)"
    DriverManager.getConnection("jdbc:duckdb:").use { c ->
        for (where in listOf("dt = '2026-11-03'", "created_at::DATE = DATE '2026-11-03'")) {
            val sql = "SELECT sum(amount_cents) FROM $scan WHERE $where"
            val plan = c.createStatement().use { s -> s.executeQuery("EXPLAIN $sql").use { rs -> rs.next(); rs.getString(2) } }
            // DuckDB prints "Scanning Files: n/total" only when it can skip files by their path
            val scanning = Regex("""Scanning Files: (\d+/\d+)""").find(plan)?.groupValues?.get(1) ?: "all ${files.size}"
            println("WHERE %-38s -> opens %s files".format(where, scanning))
        }
    }
}
