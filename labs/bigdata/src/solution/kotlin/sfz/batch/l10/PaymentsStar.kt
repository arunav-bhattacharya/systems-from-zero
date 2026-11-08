package sfz.batch.l10

import java.sql.Connection
import java.time.LocalDate

/** Captured payments for one merchant category on weekdays or on weekends. */
data class CategoryVolume(val category: String, val weekend: Boolean, val payments: Long, val amountCents: Long)

/** Captured volume for one risk tier. */
data class TierVolume(val riskTier: String, val amountCents: Long)

/** A merchant's new tracked attributes, from the onboarding service's change feed. */
data class MerchantChange(val merchantId: Int, val riskTier: String, val mcc: Int)

/**
 * Lesson batch-10: a star schema for payments in DuckDB, with a type 2 slowly changing merchant
 * dimension. The raw tables of [RawData] must already be in [c].
 *
 * The grain of the fact table is one row per payment. The merchant dimension keeps history:
 * every version of a merchant is its own row with its own surrogate key `merchant_key`, valid from
 * `valid_from` (inclusive) to `valid_to` (exclusive). The current version has `valid_to` =
 * 9999-12-31 and `is_current` = true. Validity is by day: a change effective on 2026-11-04 applies
 * to payments made on 2026-11-04 and later.
 */
class PaymentsStar(private val c: Connection) {

    /** Given: the three tables of the star, empty. */
    fun createTables() = exec(
        """CREATE TABLE dim_date (date_key INTEGER PRIMARY KEY, day DATE NOT NULL, day_name VARCHAR NOT NULL,
               is_weekend BOOLEAN NOT NULL, month INTEGER NOT NULL, quarter INTEGER NOT NULL)""",
        """CREATE TABLE dim_merchant (merchant_key INTEGER PRIMARY KEY, merchant_id INTEGER NOT NULL,
               merchant_name VARCHAR NOT NULL, mcc INTEGER NOT NULL, category VARCHAR NOT NULL,
               risk_tier VARCHAR NOT NULL, country VARCHAR NOT NULL,
               valid_from DATE NOT NULL, valid_to DATE NOT NULL, is_current BOOLEAN NOT NULL)""",
        """CREATE TABLE fact_payment (payment_id BIGINT PRIMARY KEY, date_key INTEGER NOT NULL,
               merchant_key INTEGER NOT NULL, card_country VARCHAR NOT NULL, currency VARCHAR NOT NULL,
               status VARCHAR NOT NULL, amount_cents BIGINT NOT NULL)""",
    )

    /** Given: one `dim_date` row per day for [days] days from [from]. `date_key` is yyyymmdd, e.g. 20261101. */
    fun loadDates(from: LocalDate, days: Int) = exec(
        """INSERT INTO dim_date
           SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER), d, dayname(d), dayofweek(d) IN (0, 6), month(d), quarter(d)
           FROM (SELECT CAST(DATE '$from' + CAST(i AS INTEGER) AS DATE) AS d FROM range($days) t(i))""",
    )

    /**
     * Exercise 1. The first version of every merchant in `raw_merchants`, valid from [validFrom].
     *
     * - `merchant_key` 1, 2, 3... in `merchant_id` order.
     * - `category` comes from `raw_mcc`: fold it into the dimension, so queries never join `raw_mcc`.
     * - `valid_to` is DATE '9999-12-31' and `is_current` is true.
     */
    fun loadMerchants(validFrom: LocalDate) = exec(
        // star, not snowflake: the category lookup is joined once here, not in every query
        """INSERT INTO dim_merchant
           SELECT CAST(row_number() OVER (ORDER BY m.merchant_id) AS INTEGER), m.merchant_id, m.merchant_name,
                  m.mcc, c.category, m.risk_tier, m.country, DATE '$validFrom', DATE '9999-12-31', true
           FROM raw_merchants m JOIN raw_mcc c ON c.mcc = m.mcc""",
    )

    /**
     * Exercise 2. Adds every payment of `raw_payments` that isn't in `fact_payment` yet, and returns
     * how many rows it added. Running it twice adds nothing the second time.
     *
     * - `date_key` is the yyyymmdd of `created_at`.
     * - `merchant_key` is the version of the merchant that was valid on the day of the payment,
     *   which is not always the current one: a payment can arrive late.
     */
    fun loadFacts(): Int = c.createStatement().use { s ->
        s.executeUpdate(
            """INSERT INTO fact_payment
               SELECT p.payment_id, CAST(strftime(p.created_at, '%Y%m%d') AS INTEGER), m.merchant_key,
                      p.card_country, p.currency, p.status, p.amount_cents
               FROM raw_payments p
               -- the version valid on the payment's day, not simply the current one
               JOIN dim_merchant m ON m.merchant_id = p.merchant_id
                    AND m.valid_from <= CAST(p.created_at AS DATE) AND CAST(p.created_at AS DATE) < m.valid_to
               -- idempotent: a rerun skips payments already loaded
               WHERE NOT EXISTS (SELECT 1 FROM fact_payment f WHERE f.payment_id = p.payment_id)""",
        )
    }

    /**
     * Exercise 3. A classic star query: CAPTURED payments per merchant category, split into weekdays
     * and weekends (`dim_date.is_weekend`). Sorted by category, then weekend (false first).
     */
    fun capturedByCategoryAndDayType(): List<CategoryVolume> = rows(
        """SELECT m.category, d.is_weekend, count(*), sum(f.amount_cents)
           FROM fact_payment f
           JOIN dim_date d ON d.date_key = f.date_key
           JOIN dim_merchant m ON m.merchant_key = f.merchant_key
           WHERE f.status = 'CAPTURED'
           GROUP BY m.category, d.is_weekend
           ORDER BY m.category, d.is_weekend""",
    ) { CategoryVolume(it.getString(1), it.getBoolean(2), it.getLong(3), it.getLong(4)) }

    /**
     * Exercise 4. Applies [changes] as a type 2 slowly changing dimension, effective on [effective],
     * in one transaction. Returns the number of new versions written.
     *
     * For each change whose `riskTier` or `mcc` differs from the merchant's current version: close the
     * current version (`valid_to` = [effective], `is_current` = false) and insert a new version with
     * the next free `merchant_key`, the new tier, mcc and category, the other attributes copied, valid
     * from [effective]. A change equal to the current version does nothing, so applying the same
     * changes twice writes no new versions the second time.
     */
    fun applyScd2(changes: List<MerchantChange>, effective: LocalDate): Int {
        val autoCommit = c.autoCommit
        c.autoCommit = false
        try {
            var written = 0
            for (ch in changes) {
                val current = c.prepareStatement(
                    "SELECT merchant_key, risk_tier, mcc FROM dim_merchant WHERE merchant_id = ? AND is_current"
                ).use { ps ->
                    ps.setInt(1, ch.merchantId)
                    ps.executeQuery().use { rs -> if (rs.next()) Triple(rs.getInt(1), rs.getString(2), rs.getInt(3)) else null }
                } ?: continue
                if (current.second == ch.riskTier && current.third == ch.mcc) continue      // nothing changed: no new version
                // close the current version: it was true until the day before `effective`
                c.prepareStatement("UPDATE dim_merchant SET valid_to = ?, is_current = false WHERE merchant_key = ?").use { ps ->
                    ps.setObject(1, effective)
                    ps.setInt(2, current.first)
                    ps.executeUpdate()
                }
                // the new version: a new surrogate key, the new attributes, the rest copied
                c.prepareStatement(
                    """INSERT INTO dim_merchant
                       SELECT (SELECT max(merchant_key) FROM dim_merchant) + 1, merchant_id, merchant_name, ?, ?, ?, country,
                              ?, DATE '9999-12-31', true
                       FROM dim_merchant WHERE merchant_key = ?""",
                ).use { ps ->
                    ps.setInt(1, ch.mcc)
                    ps.setString(2, RawData.category(ch.mcc))
                    ps.setString(3, ch.riskTier)
                    ps.setObject(4, effective)
                    ps.setInt(5, current.first)
                    ps.executeUpdate()
                }
                written++
            }
            c.commit()
            return written
        } catch (e: Exception) {
            c.rollback()
            throw e
        } finally {
            c.autoCommit = autoCommit
        }
    }

    /**
     * Exercise 5. CAPTURED volume per risk tier, sorted by tier.
     *
     * - [asWas] = true: each payment counts under the tier its merchant had when the payment was made
     *   (the version its `merchant_key` points at).
     * - [asWas] = false: each payment counts under its merchant's current tier, whatever it was then.
     */
    fun volumeByTier(asWas: Boolean): List<TierVolume> = rows(
        if (asWas) {
            // the fact row's own key is the version of the merchant at the time of the payment
            """SELECT m.risk_tier, sum(f.amount_cents) FROM fact_payment f
               JOIN dim_merchant m ON m.merchant_key = f.merchant_key
               WHERE f.status = 'CAPTURED' GROUP BY m.risk_tier ORDER BY m.risk_tier"""
        } else {
            // from the version to the durable id, then to today's version of the same merchant
            """SELECT cur.risk_tier, sum(f.amount_cents) FROM fact_payment f
               JOIN dim_merchant v ON v.merchant_key = f.merchant_key
               JOIN dim_merchant cur ON cur.merchant_id = v.merchant_id AND cur.is_current
               WHERE f.status = 'CAPTURED' GROUP BY cur.risk_tier ORDER BY cur.risk_tier"""
        },
    ) { TierVolume(it.getString(1), it.getLong(2)) }

    private fun exec(vararg sql: String) = c.createStatement().use { s -> sql.forEach { s.execute(it) } }

    private fun <T> rows(sql: String, map: (java.sql.ResultSet) -> T): List<T> = c.createStatement().use { s ->
        s.executeQuery(sql).use { rs -> buildList { while (rs.next()) add(map(rs)) } }
    }
}
