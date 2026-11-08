package sfz.batch.l10

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.MethodOrderer
import org.junit.jupiter.api.Order
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.api.TestMethodOrder
import sfz.bigdata.support.Duck
import sfz.bigdata.support.Duck.longOf
import java.sql.Connection
import java.time.LocalDate

/**
 * The story: the star is loaded with the payments of 1 to 3 November. On 4 November merchant 7 moves
 * from LOW to HIGH risk and merchant 42 changes category (mcc 5002 to 5012); merchant 8's record is
 * re-sent unchanged. Then the payments of 4 to 7 November load, together with one payment of
 * merchant 7 from 3 November that arrived late.
 */
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@TestMethodOrder(MethodOrderer.OrderAnnotation::class)
class Scd2Test {
    private lateinit var c: Connection
    private lateinit var star: PaymentsStar
    private val merchants = RawData.merchants()
    private val payments = RawData.payments(14_000)
    private val changeDay = LocalDate.of(2026, 11, 4)
    private val late = payments.first { it.merchantId == 7 && it.createdAt.toLocalDate() == LocalDate.of(2026, 11, 3) }
    private val changes = listOf(
        MerchantChange(7, "HIGH", 5007),
        MerchantChange(42, "MEDIUM", 5012),
        MerchantChange(8, "LOW", 5008),
    )
    private val split = payments.partition { it.createdAt.toLocalDate() < changeDay && it != late }

    @BeforeAll
    fun setUp() {
        c = Duck.connect()
        RawData.loadMerchants(c, merchants)
        RawData.loadPayments(c, split.first)
        star = PaymentsStar(c)
        star.createTables()
        star.loadDates(LocalDate.of(2026, 11, 1), 7)
    }

    /** The story, run once by the first test that needs it. Returns the number of versions applyScd2 wrote. */
    private val written: Int by lazy {
        star.loadMerchants(LocalDate.of(2026, 11, 1))
        star.loadFacts()
        val n = star.applyScd2(changes, changeDay)
        RawData.loadPayments(c, split.second)                  // the rest of the week, plus the late one
        star.loadFacts()
        n
    }

    @AfterAll
    fun tearDown() = c.close()

    private fun versions(merchantId: Int): List<List<Any?>> = c.createStatement().use { s ->
        s.executeQuery(
            "SELECT merchant_key, risk_tier, category, valid_from, valid_to, is_current FROM dim_merchant WHERE merchant_id = $merchantId ORDER BY valid_from"
        ).use { rs ->
            buildList {
                while (rs.next()) add(listOf(rs.getInt(1), rs.getString(2), rs.getString(3),
                    rs.getObject(4, LocalDate::class.java).toString(), rs.getObject(5, LocalDate::class.java).toString(), rs.getBoolean(6)))
            }
        }
    }

    @Test
    @Order(1)
    fun `a changed merchant gets a new version and the old one is closed`() {
        assertThat(written).describedAs("new versions written").isEqualTo(2)
        assertThat(versions(7)).containsExactly(
            listOf(8, "LOW", "Travel", "2026-11-01", "2026-11-04", false),
            listOf(501, "HIGH", "Travel", "2026-11-04", "9999-12-31", true),
        )
        assertThat(versions(42)).containsExactly(
            listOf(43, "MEDIUM", "Groceries", "2026-11-01", "2026-11-04", false),
            listOf(502, "MEDIUM", "Electronics", "2026-11-04", "9999-12-31", true),
        )
    }

    @Test
    @Order(2)
    fun `an unchanged merchant gets no new version, and the same changes again write nothing`() {
        written
        assertThat(versions(8)).hasSize(1)
        assertThat(star.applyScd2(changes, changeDay)).describedAs("new versions on a rerun").isZero()
        assertThat(c.longOf("SELECT count(*) FROM dim_merchant")).isEqualTo(502)
    }

    @Test
    @Order(3)
    fun `each payment points at the version valid on its day, even when it arrives late`() {
        written
        assertThat(c.longOf("SELECT count(*) FROM fact_payment")).isEqualTo(14_000)
        val keys = c.createStatement().use { s ->
            s.executeQuery(
                "SELECT f.date_key < 20261104, f.merchant_key, count(*) FROM fact_payment f JOIN dim_merchant m USING (merchant_key) " +
                    "WHERE m.merchant_id = 7 GROUP BY ALL ORDER BY 1, 2"
            ).use { rs -> buildList { while (rs.next()) add(Triple(rs.getBoolean(1), rs.getInt(2), rs.getLong(3))) } }
        }
        assertThat(keys.map { it.first to it.second }).describedAs("(before 4 Nov, merchant_key)")
            .containsExactly(false to 501, true to 8)
        assertThat(c.longOf("SELECT merchant_key FROM fact_payment WHERE payment_id = ${late.paymentId}"))
            .describedAs("the late payment from 3 November keeps the old version").isEqualTo(8)
    }

    @Test
    @Order(4)
    fun `as was keeps history in the old tier, as is moves it to today's tier`() {
        written
        val byId = merchants.associateBy { it.merchantId }
        val captured = payments.filter { it.status == "CAPTURED" }
        fun tierThen(p: RawPayment) = if (p.merchantId == 7 && p.createdAt.toLocalDate() >= changeDay) "HIGH" else byId.getValue(p.merchantId).riskTier
        fun tierNow(p: RawPayment) = if (p.merchantId == 7) "HIGH" else byId.getValue(p.merchantId).riskTier
        fun totals(tier: (RawPayment) -> String) =
            captured.groupBy(tier).map { (t, ps) -> TierVolume(t, ps.sumOf { it.amountCents }) }.sortedBy { it.riskTier }

        assertThat(star.volumeByTier(asWas = true)).isEqualTo(totals(::tierThen))
        assertThat(star.volumeByTier(asWas = false)).isEqualTo(totals(::tierNow))
        assertThat(star.volumeByTier(asWas = true)).isNotEqualTo(star.volumeByTier(asWas = false))
    }

    @Test
    @Order(5)
    fun `the versions of one merchant never overlap and leave no gap`() {
        written
        val badLinks = c.longOf(
            """SELECT count(*) FROM (
                 SELECT valid_to, lead(valid_from) OVER (PARTITION BY merchant_id ORDER BY valid_from) AS next_from
                 FROM dim_merchant) WHERE next_from IS NOT NULL AND next_from <> valid_to"""
        )
        assertThat(badLinks).describedAs("versions whose end isn't the next version's start").isZero()
        assertThat(c.longOf("SELECT count(*) FROM (SELECT merchant_id FROM dim_merchant WHERE is_current GROUP BY 1 HAVING count(*) <> 1)"))
            .describedAs("merchants without exactly one current version").isZero()
    }
}
