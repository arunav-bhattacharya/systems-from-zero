package sfz.batch.l10.demo

/**
 * On 2026-11-04 the risk team moves 50 merchants (ids 1, 11, 21, ... 491) to the HIGH tier. The
 * same change is applied to two copies of the star: type 1 (overwrite the dimension row) and
 * type 2 (close the old version, add a new one). Then both answer last week's question: how much
 * captured volume came from HIGH-risk merchants on 1 to 3 November, before the change?
 */
fun main() {
    duck().use { c ->
        rawTables(c, 1_000_000)
        buildStar(c)
        c.run("CREATE TABLE moved AS SELECT CAST(10 * k + 1 AS INTEGER) AS merchant_id FROM range(50) t(k)")
        println("before the change: " + c.rows("SELECT risk_tier, count(*) FROM dim_merchant WHERE merchant_id IN (SELECT merchant_id FROM moved) GROUP BY 1 ORDER BY 1")
            .joinToString { "${it[1]} ${it[0]}" } + " merchants are moving to HIGH")

        // type 1: overwrite. One row per merchant, no history
        c.run("CREATE TABLE dim_merchant_t1 AS SELECT * FROM dim_merchant")
        c.run("UPDATE dim_merchant_t1 SET risk_tier = 'HIGH' WHERE merchant_id IN (SELECT merchant_id FROM moved)")

        // type 2: close the current version and add a new one with a new surrogate key
        c.run("CREATE TABLE dim_merchant_t2 AS SELECT * FROM dim_merchant")
        c.run("""
            INSERT INTO dim_merchant_t2
            SELECT CAST(500 + row_number() OVER (ORDER BY merchant_id) AS INTEGER), merchant_id, merchant_name, mcc, category,
                   'HIGH', country, DATE '2026-11-04', DATE '9999-12-31', true
            FROM dim_merchant WHERE merchant_id IN (SELECT merchant_id FROM moved)""")
        c.run("""
            UPDATE dim_merchant_t2 SET valid_to = DATE '2026-11-04', is_current = false
            WHERE merchant_id IN (SELECT merchant_id FROM moved) AND merchant_key <= 500""")
        // payments from 4 November on belong to the new versions
        c.run("CREATE TABLE fact_t2 AS SELECT * FROM fact_payment")
        c.run("""
            UPDATE fact_t2 SET merchant_key = v.merchant_key
            FROM dim_merchant_t2 old, dim_merchant_t2 v
            WHERE fact_t2.merchant_key = old.merchant_key AND v.merchant_id = old.merchant_id AND v.is_current
              AND old.merchant_id IN (SELECT merchant_id FROM moved) AND fact_t2.date_key >= 20261104""")

        println("merchant 1 in the type 2 dimension:")
        c.rows("SELECT merchant_key, risk_tier, valid_from, valid_to, is_current FROM dim_merchant_t2 WHERE merchant_id = 1 ORDER BY valid_from")
            .forEach { println("  merchant_key=%-4s risk_tier=%-6s valid %s to %s, is_current=%s".format(it[0], it[1], it[2], it[3], it[4])) }

        fun highBeforeChange(fact: String, dim: String) = c.rows("""
            SELECT sum(f.amount_cents) FROM $fact f JOIN $dim m ON m.merchant_key = f.merchant_key
            WHERE f.status = 'CAPTURED' AND m.risk_tier = 'HIGH' AND f.date_key < 20261104""").first()[0] as Number
        val t1 = highBeforeChange("fact_payment", "dim_merchant_t1").toLong()
        val t2 = highBeforeChange("fact_t2", "dim_merchant_t2").toLong()
        val then = highBeforeChange("fact_payment", "dim_merchant").toLong()
        println("HIGH-risk captured volume on 1 to 3 November:")
        println("  what the report said on 3 November:  %,16d cents".format(then))
        println("  type 1, asked again after the change: %,16d cents (+%.0f%%)".format(t1, 100.0 * (t1 - then) / then))
        println("  type 2, asked again after the change: %,16d cents".format(t2))
    }
}
