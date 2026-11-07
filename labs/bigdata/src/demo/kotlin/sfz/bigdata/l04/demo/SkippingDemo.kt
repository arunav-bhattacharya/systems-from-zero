package sfz.bigdata.l04.demo

import org.apache.spark.sql.functions.col

/**
 * The same filter on the same 400,000 payments, stored sorted by amount and in random order.
 * Spark reports how many rows its scan handed on; DuckDB reports how many bytes it read.
 */
fun main() {
    PaymentParquet.open().use { duck ->
        val spark = demoSpark()
        println("SELECT merchant_id, amount_cents WHERE amount_cents > 240000")
        for (file in listOf(PaymentParquet.sorted, PaymentParquet.random)) {
            val query = spark.read().parquet(file.absolutePath)
                .where(col("amount_cents").gt(240_000))
                .select("merchant_id", "amount_cents")
            val matching = query.collectAsList().size
            if (file == PaymentParquet.sorted) println("Spark's PushedFilters: [${pushedFilters(query)}]")
            val profile = duck.rows("EXPLAIN ANALYZE SELECT merchant_id, amount_cents FROM '${file.absolutePath}' WHERE amount_cents > 240000")
                .joinToString("\n") { it[1] ?: "" }
            val read = Regex("""Data Read:\s*([\d.]+ [kMG]?B)""").find(profile)?.groupValues?.get(1)
            println("%-15s Spark scan handed on %,7d rows, %,d match.  DuckDB read %s".format(file.name, scanRows(query), matching, read))
        }
        spark.stop()
    }
}
