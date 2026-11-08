package sfz.batch.l10.demo

import java.io.File

/**
 * The same million payments stored two ways as Parquet: a star (a fact file and two small
 * dimension files) and one big table, with every dimension column copied onto every fact row.
 * Compares the bytes on disk, the time of the same question, and what one correction costs.
 */
fun main() {
    val dir = File(DEMO_DIR, "obt").apply { deleteRecursively(); mkdirs() }
    duck().use { c ->
        rawTables(c, 1_000_000)
        buildStar(c)
        // one big table: the joins done once, at write time
        c.run("""
            CREATE TABLE obt AS
            SELECT f.*, d.day, d.day_name, d.is_weekend, d.month, d.quarter,
                   m.merchant_id, m.merchant_name, m.mcc, m.category, m.risk_tier, m.country
            FROM fact_payment f
            JOIN dim_date d ON d.date_key = f.date_key
            JOIN dim_merchant m ON m.merchant_key = f.merchant_key
            ORDER BY f.date_key, f.payment_id""")
        for (t in listOf("fact_payment", "dim_date", "dim_merchant", "obt")) {
            File(dir, t).mkdirs()
            c.run("COPY $t TO '${File(dir, "$t/data.parquet").absolutePath}' (FORMAT parquet)")
        }
        fun p(t: String) = "read_parquet('${File(dir, "$t/data.parquet").absolutePath}')"
        val star = megabytes(File(dir, "fact_payment")) + megabytes(File(dir, "dim_date")) + megabytes(File(dir, "dim_merchant"))
        println("on disk: star %.1f MB (fact %.1f MB, dimensions %.3f MB), one big table %.1f MB".format(
            star, megabytes(File(dir, "fact_payment")), megabytes(File(dir, "dim_date")) + megabytes(File(dir, "dim_merchant")),
            megabytes(File(dir, "obt"))))
        val columns = c.rows("SELECT count(*) FROM information_schema.columns WHERE table_name = 'obt'").first()[0]
        println("one big table: $columns columns; the fact table: 7")

        val starQuery = """
            SELECT m.category, d.is_weekend, count(*), sum(f.amount_cents)
            FROM ${p("fact_payment")} f
            JOIN ${p("dim_date")} d ON d.date_key = f.date_key
            JOIN ${p("dim_merchant")} m ON m.merchant_key = f.merchant_key
            WHERE f.status = 'CAPTURED' GROUP BY ALL ORDER BY 1, 2"""
        val obtQuery = """
            SELECT category, is_weekend, count(*), sum(amount_cents)
            FROM ${p("obt")} WHERE status = 'CAPTURED' GROUP BY ALL ORDER BY 1, 2"""
        val (a, ta) = best(7) { c.rows(starQuery) }
        val (b, tb) = best(7) { c.rows(obtQuery) }
        println("same question from Parquet, best of 7: star with 2 joins %.0f ms, one big table %.0f ms, same answer: %s".format(ta, tb, a == b))

        // a correction: merchant 7's category was wrong all along
        val obtRows = c.rows("SELECT count(*) FROM obt WHERE merchant_id = 7").first()[0]
        val obtGroups = c.rows("SELECT count(DISTINCT row_group_id) FROM parquet_metadata('${File(dir, "obt/data.parquet").absolutePath}')").first()[0]
        // the row groups whose min/max for merchant_id can't rule merchant 7 out: all of them must be rewritten
        val touched = c.rows("""
            SELECT count(*) FROM parquet_metadata('${File(dir, "obt/data.parquet").absolutePath}')
            WHERE path_in_schema = 'merchant_id'
              AND CAST(stats_min_value AS INTEGER) <= 7 AND CAST(stats_max_value AS INTEGER) >= 7""").first()[0]
        println("fix merchant 7's category: star rewrites 1 row of dim_merchant (500 rows);")
        println("  one big table rewrites $obtRows rows of merchant 7, spread over $touched of its $obtGroups row groups")
    }
}
