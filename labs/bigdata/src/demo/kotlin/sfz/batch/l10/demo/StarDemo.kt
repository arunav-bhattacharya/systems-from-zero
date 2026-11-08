package sfz.batch.l10.demo

/**
 * A million payments in their operational shape, then the same data as a star: one fact table of
 * events and two dimension tables. Prints the shape of each table, one fact row with the dimension
 * rows it points at, and the analyst's question asked of both.
 */
fun main() {
    duck().use { c ->
        rawTables(c, 1_000_000)
        buildStar(c)
        println("%-14s %10s %8s".format("table", "rows", "columns"))
        for (t in listOf("raw_payments", "raw_merchants", "raw_mcc", "fact_payment", "dim_date", "dim_merchant")) {
            val rows = c.rows("SELECT count(*) FROM $t").first()[0]
            val cols = c.rows("SELECT count(*) FROM information_schema.columns WHERE table_name = '$t'").first()[0]
            println("%-14s %,10d %8s".format(t, rows, cols))
        }

        val f = c.rows("SELECT * FROM fact_payment WHERE payment_id = 3").first()
        println("one fact row:        payment_id=${f[0]} date_key=${f[1]} merchant_key=${f[2]} card_country=${f[3]} currency=${f[4]} status=${f[5]} amount_cents=${f[6]}")
        val d = c.rows("SELECT day, day_name, is_weekend, quarter FROM dim_date WHERE date_key = ${f[1]}").first()
        println("  its dim_date row:  day=${d[0]} day_name=${d[1]} is_weekend=${d[2]} quarter=${d[3]}")
        val m = c.rows("SELECT merchant_id, merchant_name, category, risk_tier, country FROM dim_merchant WHERE merchant_key = ${f[2]}").first()
        println("  its dim_merchant:  merchant_id=${m[0]} name='${m[1]}' category=${m[2]} risk_tier=${m[3]} country=${m[4]}")

        // the analyst's question: captured volume per category, weekdays against weekends
        val operational = """
            SELECT c.category, dayofweek(p.created_at) IN (0, 6) AS weekend, count(*), sum(p.amount_cents)
            FROM raw_payments p
            JOIN raw_merchants m ON m.merchant_id = p.merchant_id
            JOIN raw_mcc c ON c.mcc = m.mcc
            WHERE p.status = 'CAPTURED'
            GROUP BY ALL ORDER BY 1, 2"""
        val star = """
            SELECT m.category, d.is_weekend, count(*), sum(f.amount_cents)
            FROM fact_payment f
            JOIN dim_date d ON d.date_key = f.date_key
            JOIN dim_merchant m ON m.merchant_key = f.merchant_key
            WHERE f.status = 'CAPTURED'
            GROUP BY ALL ORDER BY 1, 2"""
        val (a, ta) = best { c.rows(operational) }
        val (b, tb) = best { c.rows(star) }
        println("captured volume by category and day type (star schema, best of 5: %.0f ms):".format(tb))
        for (r in b) println("  %-12s weekend=%-5s %,8d payments %,18d cents".format(r[0], r[1], r[2], r[3]))
        println("the operational tables give the same answer: ${a == b} (best of 5: %.0f ms)".format(ta))
    }
}
