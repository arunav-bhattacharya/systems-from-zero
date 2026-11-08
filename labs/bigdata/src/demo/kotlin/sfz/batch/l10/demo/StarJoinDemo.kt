package sfz.batch.l10.demo

/**
 * How an engine runs a star join. The fact table (4 million payments, stored in date order) is
 * joined to two small dimensions with filters on the dimensions only. Prints what DuckDB's scan of
 * the fact table did: the filter the join pushed into it at run time, the row groups it read, and
 * the rows it produced. Then the same query with that run-time filter switched off.
 */
fun main() {
    duck().use { c ->
        rawTables(c, 4_000_000)
        buildStar(c)
        val query = """
            SELECT sum(f.amount_cents)
            FROM fact_payment f
            JOIN dim_date d ON d.date_key = f.date_key
            JOIN dim_merchant m ON m.merchant_key = f.merchant_key
            WHERE d.is_weekend AND m.risk_tier = 'HIGH' AND f.status = 'CAPTURED'"""
        val answer = c.rows(query).first()[0]
        println("captured weekend volume of HIGH-risk merchants: %,d cents".format(answer))
        report(c, query, "with run-time join filters (the default)")
        c.run("SET disabled_optimizers = 'join_filter_pushdown'")
        report(c, query, "with join_filter_pushdown switched off")
    }
}

/** Prints the lines of `EXPLAIN ANALYZE` that describe the scan of `fact_payment`. */
private fun report(c: java.sql.Connection, query: String, label: String) {
    val plan = c.rows("EXPLAIN ANALYZE $query").first()[1].toString()
    // the plan is drawn as boxes; keep the left-most box of each line, which holds the fact scan
    val lines = plan.lines().map { it.substringAfter("│").substringBefore("│").trim() }
    val start = lines.indexOfFirst { it == "Table: memory.main.fact_payment" }
    val box = lines.drop(start).takeWhile { it.isNotEmpty() && !it.startsWith("╰") }
    println("$label, the fact table's scan:")
    box.filter { "Filters" in it || "optional" in it || "Row Groups" in it || "rows" in it || it.startsWith("(") }
        .forEach { println("  " + it.replace(Regex("\\s+\\d+(\\.\\d+)?(µs|ms|s)$"), "")) }
}
