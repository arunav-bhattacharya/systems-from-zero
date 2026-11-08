package sfz.batch.l10

import java.sql.Connection
import java.time.LocalDate
import java.time.LocalDateTime
import kotlin.random.Random

/** One payment as the payments service stores it: the operational row, before any modelling. */
data class RawPayment(
    val paymentId: Long,
    val merchantId: Int,
    val cardCountry: String,
    val currency: String,
    val amountCents: Long,
    val status: String,
    /** UTC. */
    val createdAt: LocalDateTime,
)

/** One merchant as the onboarding service stores it. */
data class RawMerchant(val merchantId: Int, val merchantName: String, val mcc: Int, val riskTier: String, val country: String)

/**
 * Lesson batch-10 (given): the operational data the star is built from, the same rows on every run.
 * Read it, but you don't need to change it.
 *
 * Three raw tables, shaped the way the services keep them:
 *
 * ```
 * raw_payments (payment_id BIGINT, merchant_id INTEGER, card_country VARCHAR, currency VARCHAR,
 *               amount_cents BIGINT, status VARCHAR, created_at TIMESTAMP)
 * raw_merchants(merchant_id INTEGER, merchant_name VARCHAR, mcc INTEGER, risk_tier VARCHAR, country VARCHAR)
 * raw_mcc      (mcc INTEGER, category VARCHAR)        -- the category lookup, a separate table
 * ```
 */
object RawData {
    val COUNTRIES = listOf("NL", "DE", "FR", "GB", "US", "IN", "BR", "JP")
    val CURRENCIES = listOf("EUR", "USD", "GBP", "INR")
    /** CAPTURED appears twice, so about 40% of payments are captured. */
    val STATUSES = listOf("AUTHORIZED", "CAPTURED", "CAPTURED", "DECLINED", "REFUNDED")

    /** The category of a merchant category code: 5000 to 5004 Groceries, 5005 to 5009 Travel, and so on. */
    fun category(mcc: Int): String = listOf("Groceries", "Travel", "Electronics", "Gaming")[(mcc - 5_000) / 5]

    /**
     * [n] merchants. Merchant m has mcc 5000 + m mod 20, risk tier HIGH if m mod 10 = 0, MEDIUM if
     * m mod 3 = 0 (and not HIGH), LOW otherwise, and country NL, DE, FR or GB by m mod 4.
     */
    fun merchants(n: Int = 500): List<RawMerchant> = (0 until n).map { m ->
        val tier = when {
            m % 10 == 0 -> "HIGH"
            m % 3 == 0 -> "MEDIUM"
            else -> "LOW"
        }
        RawMerchant(m, "Merchant $m", 5_000 + m % 20, tier, listOf("NL", "DE", "FR", "GB")[m % 4])
    }

    /** [n] payments spread evenly over [days] days from [firstDay] (UTC): payment i is on day i mod [days]. */
    fun payments(n: Int, days: Int = 7, firstDay: LocalDate = LocalDate.of(2026, 11, 1), merchants: Int = 500, seed: Long = 42): List<RawPayment> {
        val rnd = Random(seed)
        return (0 until n).map { i ->
            val day = firstDay.plusDays((i % days).toLong())
            RawPayment(
                paymentId = i.toLong(),
                merchantId = rnd.nextInt(merchants),
                cardCountry = COUNTRIES[rnd.nextInt(COUNTRIES.size)],
                currency = CURRENCIES[rnd.nextInt(CURRENCIES.size)],
                amountCents = 100L + rnd.nextLong(250_000),
                status = STATUSES[rnd.nextInt(STATUSES.size)],
                createdAt = day.atStartOfDay().plusSeconds(rnd.nextLong(86_400)),
            )
        }
    }

    /** Creates the three raw tables in [c] (if missing) and loads [merchants] and their categories. */
    fun loadMerchants(c: Connection, merchants: List<RawMerchant>) {
        createRawTables(c)
        insert(c, "raw_merchants", merchants.map { "(${it.merchantId}, '${it.merchantName}', ${it.mcc}, '${it.riskTier}', '${it.country}')" })
        insert(c, "raw_mcc", (5_000 until 5_020).map { "($it, '${category(it)}')" })
    }

    /** Appends [payments] to `raw_payments` (creating the raw tables if they are missing). */
    fun loadPayments(c: Connection, payments: List<RawPayment>) {
        createRawTables(c)
        insert(c, "raw_payments", payments.map {
            "(${it.paymentId}, ${it.merchantId}, '${it.cardCountry}', '${it.currency}', ${it.amountCents}, '${it.status}', TIMESTAMP '${it.createdAt}')"
        })
    }

    private fun createRawTables(c: Connection) = c.createStatement().use { s ->
        s.execute("""CREATE TABLE IF NOT EXISTS raw_payments (payment_id BIGINT, merchant_id INTEGER, card_country VARCHAR,
                     currency VARCHAR, amount_cents BIGINT, status VARCHAR, created_at TIMESTAMP)""")
        s.execute("CREATE TABLE IF NOT EXISTS raw_merchants (merchant_id INTEGER, merchant_name VARCHAR, mcc INTEGER, risk_tier VARCHAR, country VARCHAR)")
        s.execute("CREATE TABLE IF NOT EXISTS raw_mcc (mcc INTEGER, category VARCHAR)")
    }

    private fun insert(c: Connection, table: String, values: List<String>) = c.createStatement().use { s ->
        for (chunk in values.chunked(1_000)) s.execute("INSERT INTO $table VALUES " + chunk.joinToString(", "))
    }
}
