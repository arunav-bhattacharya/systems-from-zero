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
import java.time.DayOfWeek
import java.time.LocalDate

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
@TestMethodOrder(MethodOrderer.OrderAnnotation::class)
class StarSchemaTest {
    private lateinit var c: Connection
    private lateinit var star: PaymentsStar
    private val merchants = RawData.merchants()
    private val payments = RawData.payments(20_000)            // 7 days from Sunday 2026-11-01

    @BeforeAll
    fun setUp() {
        c = Duck.connect()
        RawData.loadMerchants(c, merchants)
        RawData.loadPayments(c, payments)
        star = PaymentsStar(c)
        star.createTables()
        star.loadDates(LocalDate.of(2026, 11, 1), 7)
    }

    // your code runs inside the tests, so each test reports the exercise it is waiting for
    private val merchantsLoaded by lazy { star.loadMerchants(LocalDate.of(2026, 11, 1)) }
    private val factsLoaded by lazy { merchantsLoaded; star.loadFacts() }

    @AfterAll
    fun tearDown() = c.close()

    @Test
    @Order(1)
    fun `the merchant dimension has one current version per merchant, with the category folded in`() {
        merchantsLoaded
        assertThat(c.longOf("SELECT count(*) FROM dim_merchant")).isEqualTo(500)
        assertThat(c.longOf("SELECT count(*) FROM dim_merchant WHERE is_current AND valid_to = DATE '9999-12-31'")).isEqualTo(500)
        assertThat(c.longOf("SELECT count(DISTINCT merchant_key) FROM dim_merchant WHERE merchant_key BETWEEN 1 AND 500")).isEqualTo(500)
        c.createStatement().use { s ->
            s.executeQuery("SELECT merchant_key, mcc, category, risk_tier, valid_from FROM dim_merchant WHERE merchant_id = 7").use { rs ->
                assertThat(rs.next()).isTrue()
                assertThat(rs.getInt(1)).describedAs("keys follow merchant_id order").isEqualTo(8)
                assertThat(rs.getInt(2)).isEqualTo(5007)
                assertThat(rs.getString(3)).describedAs("the category from raw_mcc, in the dimension itself").isEqualTo("Travel")
                assertThat(rs.getString(4)).isEqualTo("LOW")
                assertThat(rs.getObject(5, LocalDate::class.java)).isEqualTo(LocalDate.of(2026, 11, 1))
            }
        }
    }

    @Test
    @Order(2)
    fun `every payment becomes one fact row that finds its day and its merchant`() {
        assertThat(factsLoaded).describedAs("rows added by the first load").isEqualTo(20_000)
        assertThat(c.longOf("SELECT count(*) FROM fact_payment")).isEqualTo(20_000)
        assertThat(c.longOf("SELECT count(*) FROM fact_payment f WHERE NOT EXISTS (SELECT 1 FROM dim_date d WHERE d.date_key = f.date_key)"))
            .describedAs("facts with no date row").isZero()
        assertThat(c.longOf("SELECT count(*) FROM fact_payment f WHERE NOT EXISTS (SELECT 1 FROM dim_merchant m WHERE m.merchant_key = f.merchant_key)"))
            .describedAs("facts with no merchant row").isZero()
        assertThat(c.longOf("SELECT date_key FROM fact_payment WHERE payment_id = 6")).isEqualTo(20261107)
        val p = payments[1234]
        assertThat(c.longOf("SELECT m.merchant_id FROM fact_payment f JOIN dim_merchant m USING (merchant_key) WHERE payment_id = 1234"))
            .isEqualTo(p.merchantId.toLong())
    }

    @Test
    @Order(3)
    fun `loading the facts again adds nothing`() {
        factsLoaded
        assertThat(star.loadFacts()).describedAs("rows added by a rerun").isZero()
        assertThat(c.longOf("SELECT count(*) FROM fact_payment")).isEqualTo(20_000)
    }

    @Test
    @Order(4)
    fun `captured volume by category and day type matches the raw payments`() {
        factsLoaded
        val byId = merchants.associateBy { it.merchantId }
        val expected = payments.filter { it.status == "CAPTURED" }
            .groupBy { RawData.category(byId.getValue(it.merchantId).mcc) to (it.createdAt.dayOfWeek in setOf(DayOfWeek.SATURDAY, DayOfWeek.SUNDAY)) }
            .map { (k, ps) -> CategoryVolume(k.first, k.second, ps.size.toLong(), ps.sumOf { it.amountCents }) }
            .sortedWith(compareBy({ it.category }, { it.weekend }))
        val answer = star.capturedByCategoryAndDayType()
        assertThat(answer).hasSize(8)
        assertThat(answer).isEqualTo(expected)
    }
}
