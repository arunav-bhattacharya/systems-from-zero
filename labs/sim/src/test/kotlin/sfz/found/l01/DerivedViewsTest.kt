package sfz.found.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import java.nio.file.Path

class DerivedViewsTest {
    @TempDir
    lateinit var dir: Path

    private fun auth(id: String, merchant: String, day: String, cents: Long) =
        PaymentEvent(id, merchant, day, Kind.AUTHORIZED, cents)

    private fun PaymentEvent.then(kind: Kind, day: String = this.day) = copy(kind = kind, day = day)

    /** The slow path behind the cache: read the whole log and add up one merchant's money. */
    private fun balanceFromLog(log: PaymentLog, merchant: String): Long {
        var sum = 0L
        log.replay { _, e ->
            if (e.merchant == merchant) when (e.kind) {
                Kind.CAPTURED -> sum += e.amountCents
                Kind.REFUNDED -> sum -= e.amountCents
                Kind.AUTHORIZED -> {}
            }
        }
        return sum
    }

    @Test
    fun `the index holds the latest status of a payment and the amount it was authorized for`() {
        val index = PaymentIndex()
        val a = auth("pay-000001", "m-cafe", "2026-03-02", 4000)
        index.apply(a)
        assertThat(index.get("pay-000001")).isEqualTo(PaymentState("m-cafe", 4000, Kind.AUTHORIZED))
        index.apply(a.then(Kind.CAPTURED))
        index.apply(a.then(Kind.REFUNDED, "2026-03-03"))
        assertThat(index.get("pay-000001")).isEqualTo(PaymentState("m-cafe", 4000, Kind.REFUNDED))
        assertThat(index.size).isEqualTo(1)
    }

    @Test
    fun `the index says null for a payment the log never mentioned`() {
        val index = PaymentIndex()
        index.apply(auth("pay-000001", "m-cafe", "2026-03-02", 4000))
        assertThat(index.get("pay-999999")).isNull()
    }

    @Test
    fun `daily totals add captures and take refunds off on the day of the refund`() {
        val totals = DailyTotals()
        val a = auth("pay-000001", "m-cafe", "2026-03-02", 4000)
        val b = auth("pay-000002", "m-cafe", "2026-03-02", 1250)
        for (e in listOf(a, b, a.then(Kind.CAPTURED), b.then(Kind.CAPTURED), a.then(Kind.REFUNDED, "2026-03-03"))) {
            totals.apply(e)
        }
        assertThat(totals.total("m-cafe", "2026-03-02")).isEqualTo(5250)
        assertThat(totals.total("m-cafe", "2026-03-03")).isEqualTo(-4000)
        assertThat(totals.total("m-books", "2026-03-02")).isEqualTo(0)
    }

    @Test
    fun `an authorization alone moves no money`() {
        val totals = DailyTotals()
        totals.apply(auth("pay-000001", "m-cafe", "2026-03-02", 4000))
        assertThat(totals.total("m-cafe", "2026-03-02")).isEqualTo(0)
    }

    @Test
    fun `the cache runs the slow path once and then answers from memory`() {
        val cache = BalanceCache { 4000L }
        assertThat(cache.get("m-cafe")).isEqualTo(4000)
        assertThat(cache.get("m-cafe")).isEqualTo(4000)
        assertThat(cache.loads).isEqualTo(1)
    }

    @Test
    fun `a new event makes the cache forget that merchant and only that merchant`() {
        val log = PaymentLog(dir.resolve("payments.log"))
        val cache = BalanceCache { m -> balanceFromLog(log, m) }
        val service = PaymentService(log, listOf(cache))
        val a = auth("pay-000001", "m-cafe", "2026-03-02", 4000)
        service.record(a)
        service.record(a.then(Kind.CAPTURED))
        service.record(auth("pay-000002", "m-books", "2026-03-02", 900).then(Kind.CAPTURED))
        assertThat(cache.get("m-cafe")).isEqualTo(4000)
        assertThat(cache.get("m-books")).isEqualTo(900)
        assertThat(cache.loads).isEqualTo(2)

        service.record(a.then(Kind.REFUNDED, "2026-03-03"))      // m-cafe's cached 4000 is now wrong
        assertThat(cache.get("m-cafe")).isEqualTo(0)
        assertThat(cache.get("m-books")).isEqualTo(900)          // still cached: no reload
        assertThat(cache.loads).isEqualTo(3)
    }

    @Test
    fun `views rebuilt from the log give the same answers as the live ones`() {
        val log = PaymentLog(dir.resolve("payments.log"))
        val liveIndex = PaymentIndex()
        val liveTotals = DailyTotals()
        val service = PaymentService(log, listOf(liveIndex, liveTotals))
        val events = Payments.events(seed = 42, payments = 2_000)
        events.forEach { service.record(it) }

        val index = PaymentIndex()
        val totals = DailyTotals()
        rebuild(log, index, totals)

        assertThat(index.size).isEqualTo(liveIndex.size).isEqualTo(2_000)
        for (id in events.map { it.paymentId }.distinct()) assertThat(index.get(id)).isEqualTo(liveIndex.get(id))
        for (m in Payments.merchants) for (d in Payments.days) {
            assertThat(totals.total(m, d)).`as`("$m on $d").isEqualTo(liveTotals.total(m, d))
        }
    }

    @Test
    fun `rebuilding twice does not count anything twice`() {
        val log = PaymentLog(dir.resolve("payments.log"))
        Payments.events(seed = 7, payments = 300).forEach { log.append(it) }
        val totals = DailyTotals()
        rebuild(log, totals)
        val first = Payments.days.map { totals.total("m-cafe", it) }
        rebuild(log, totals)
        assertThat(Payments.days.map { totals.total("m-cafe", it) }).isEqualTo(first)
    }

    @Test
    fun `after a restart the log is all you need`() {
        val file = dir.resolve("payments.log")
        val before = DailyTotals()
        val service = PaymentService(PaymentLog(file), listOf(before))
        Payments.events(seed = 3, payments = 500).forEach { service.record(it) }

        // the process dies: every view in memory is gone. A new process opens the same file.
        val reopened = PaymentLog(file)
        val after = DailyTotals()
        val index = PaymentIndex()
        val cache = BalanceCache { m -> balanceFromLog(reopened, m) }
        rebuild(reopened, after, index, cache)

        assertThat(index.size).isEqualTo(500)
        for (m in Payments.merchants) {
            for (d in Payments.days) assertThat(after.total(m, d)).isEqualTo(before.total(m, d))
            assertThat(cache.get(m)).isEqualTo(Payments.days.sumOf { before.total(m, it) })
        }
    }
}
