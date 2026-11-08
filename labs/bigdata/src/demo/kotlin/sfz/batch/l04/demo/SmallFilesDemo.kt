package sfz.batch.l04.demo

import java.io.File
import java.sql.Connection
import java.sql.DriverManager

/** The same week of payments stored as 7 files and as 350 small ones, then queried the same way. */
fun main() {
    DriverManager.getConnection("jdbc:duckdb:").use { c ->
        // 70,000 payments, 10,000 a day for 7 days
        c.run("""CREATE TABLE payments AS
                 SELECT i AS payment_id, (hash(i) % 250000 + 100)::BIGINT AS amount_cents,
                        DATE '2026-11-01' + (i // 10000)::INTEGER AS dt
                 FROM range(70000) t(i)""")
        val few = fresh("build/l03/few-files")
        val many = fresh("build/l03/many-files")
        for (day in 0 until 7) {
            val dt = "2026-11-0${day + 1}"
            // one file per day, as a daily batch job would write it
            c.copy("SELECT payment_id, amount_cents FROM payments WHERE dt = DATE '$dt'", File(few, "dt=$dt/part-0.parquet"))
            // 50 files per day, as a job with 50 tasks (or a stream writing every half hour) would
            for (part in 0 until 50) {
                c.copy("SELECT payment_id, amount_cents FROM payments WHERE dt = DATE '$dt' AND payment_id % 50 = $part",
                    File(many, "dt=$dt/part-$part.parquet"))
            }
        }
        for (root in listOf(few, many)) {
            val sql = "SELECT dt, sum(amount_cents) FROM read_parquet('${root.absolutePath}/**/*.parquet') GROUP BY dt"
            val best = (1..5).minOf {
                val t0 = System.nanoTime()
                c.createStatement().use { s -> s.executeQuery(sql).use { rs -> while (rs.next()) Unit } }
                (System.nanoTime() - t0) / 1e6
            }
            val files = root.walkTopDown().filter { it.name.endsWith(".parquet") }.toList()
            println("%-10s %4d files, %4.1f MB, query %5.1f ms".format(root.name, files.size, files.sumOf { it.length() } / 1e6, best))
        }
    }
}

private fun fresh(path: String) = File(path).apply { deleteRecursively(); mkdirs() }

private fun Connection.run(sql: String) = createStatement().use { it.execute(sql) }

private fun Connection.copy(select: String, file: File) {
    file.parentFile.mkdirs()
    run("COPY ($select) TO '${file.absolutePath}' (FORMAT parquet)")
}
