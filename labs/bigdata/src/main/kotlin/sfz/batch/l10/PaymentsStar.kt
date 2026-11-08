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
    fun loadMerchants(validFrom: LocalDate) {
        TODO("Exercise 1: INSERT INTO dim_merchant ... SELECT from raw_merchants joined to raw_mcc")
    }

    /**
     * Exercise 2. Adds every payment of `raw_payments` that isn't in `fact_payment` yet, and returns
     * how many rows it added. Running it twice adds nothing the second time.
     *
     * - `date_key` is the yyyymmdd of `created_at`.
     * - `merchant_key` is the version of the merchant that was valid on the day of the payment,
     *   which is not always the current one: a payment can arrive late.
     */
    fun loadFacts(): Int {
        TODO("Exercise 2: INSERT INTO fact_payment the payments not loaded yet, each with the merchant version valid on its day")
    }

    /**
     * Exercise 3. A classic star query: CAPTURED payments per merchant category, split into weekdays
     * and weekends (`dim_date.is_weekend`). Sorted by category, then weekend (false first).
     */
    fun capturedByCategoryAndDayType(): List<CategoryVolume> {
        TODO("Exercise 3: join the fact to dim_date and dim_merchant, filter CAPTURED, group by category and is_weekend")
    }

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
        TODO("Exercise 4: for each real change, close the current version and insert a new one, in one transaction")
    }

    /**
     * Exercise 5. CAPTURED volume per risk tier, sorted by tier.
     *
     * - [asWas] = true: each payment counts under the tier its merchant had when the payment was made
     *   (the version its `merchant_key` points at).
     * - [asWas] = false: each payment counts under its merchant's current tier, whatever it was then.
     */
    fun volumeByTier(asWas: Boolean): List<TierVolume> {
        TODO("Exercise 5: group by the tier of the version the fact points at (as was) or of the current version (as is)")
    }

    private fun exec(vararg sql: String) = c.createStatement().use { s -> sql.forEach { s.execute(it) } }

    private fun <T> rows(sql: String, map: (java.sql.ResultSet) -> T): List<T> = c.createStatement().use { s ->
        s.executeQuery(sql).use { rs -> buildList { while (rs.next()) add(map(rs)) } }
    }
}
