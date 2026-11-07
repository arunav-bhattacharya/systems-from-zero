package sfz.nosql.l08

import com.mongodb.ExplainVerbosity
import com.mongodb.MongoWriteException
import com.mongodb.client.MongoCollection
import com.mongodb.client.model.Filters
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.bson.BsonDocument
import org.bson.Document
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import sfz.nosql.support.TestMongo
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset
import java.util.concurrent.Callable
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class PaymentDocsTest {
    private val t0: Instant = Instant.parse("2026-11-07T00:00:00Z")

    // 1,000 payments, one every two minutes from 2026-11-07 00:00 UTC (so into the next day),
    // for 50 accounts and 5 merchants; every seventh one failed. Same shape as lesson 2's seed.
    private val seed: List<Payment> = (0 until 1_000).map { i ->
        Payment(
            paymentId = "pay-${81_000 + i}",
            accountId = "A-${1_001 + i % 50}",
            merchantId = "M-00${40 + i % 5}",
            status = if (i % 7 == 3) "FAILED" else "SETTLED",
            amountMinor = 500L + (i * 7_919L) % 9_501,
            currency = "EUR",
            createdAt = t0.plusSeconds(i * 120L),
        )
    }
    private lateinit var payments: MongoCollection<Document>

    @BeforeAll
    fun seedOnce() {
        payments = PaymentDocs.createCollection(TestMongo.freshDatabase("l08"))
        payments.insertMany(seed.map(PaymentDocs::toDocument))
        PaymentDocs.createIndexes(payments)
    }

    /** A collection of its own, for the tests that write. */
    private fun fresh(): MongoCollection<Document> = PaymentDocs.createCollection(TestMongo.freshDatabase("l08w"))

    private fun settled(id: String, amount: Long = 10_000, refunds: List<Refund> = emptyList()) =
        Payment(id, "A-1001", "M-0042", "SETTLED", amount, "EUR", t0, refunds)

    @Test
    fun `toDocument stores a payment as one document with its refunds embedded, in the types the schema wants`() {
        val coll = fresh()
        val refunds = listOf(Refund("ref-1", 1_500, t0.plusSeconds(60)), Refund("ref-2", 500, t0.plusSeconds(120)))
        coll.insertOne(PaymentDocs.toDocument(settled("pay-81723", refunds = refunds)))

        // read it back as raw BSON, so we see the stored types, not what Kotlin would convert them to
        val raw = coll.withDocumentClass(BsonDocument::class.java).find(Filters.eq("_id", "pay-81723")).first()!!
        assertThat(raw.getString("_id").value).isEqualTo("pay-81723")
        assertThat(raw["amountMinor"]!!.isInt64).`as`("amountMinor is a BSON long").isTrue()
        assertThat(raw["createdAt"]!!.isDateTime).`as`("createdAt is a BSON date").isTrue()
        assertThat(raw.getInt64("refundedMinor").value).isEqualTo(2_000)
        val embedded = raw.getArray("refunds").map { it.asDocument() }
        assertThat(embedded.map { it.getString("refundId").value }).containsExactly("ref-1", "ref-2")
        assertThat(embedded.all { it["at"]!!.isDateTime && it["amountMinor"]!!.isInt64 }).isTrue()
        assertThat(coll.countDocuments()).isEqualTo(1)
    }

    @Test
    fun `the validator rejects documents that break the schema`() {
        val coll = fresh()
        fun rejected(p: Payment) = assertThatThrownBy { coll.insertOne(PaymentDocs.toDocument(p)) }
            .isInstanceOf(MongoWriteException::class.java)
            .satisfies({ assertThat((it as MongoWriteException).code).isEqualTo(121) }) // DocumentValidationFailure

        rejected(settled("pay-1", amount = 0))
        rejected(settled("pay-2").copy(status = "PENDING"))
        rejected(settled("pay-3").copy(currency = "EURO"))
        rejected(settled("pay-4", refunds = (1..21).map { Refund("ref-$it", 10, t0) })) // the array is bounded
        coll.insertOne(PaymentDocs.toDocument(settled("pay-5", refunds = (1..20).map { Refund("ref-$it", 10, t0) })))
        assertThat(coll.countDocuments()).isEqualTo(1)
    }

    @Test
    fun `addRefund pushes the refund and raises refundedMinor in one update`() {
        val coll = fresh()
        coll.insertOne(PaymentDocs.toDocument(settled("pay-81723", amount = 4_250)))

        assertThat(PaymentDocs.addRefund(coll, "pay-81723", Refund("ref-1", 1_250, t0.plusSeconds(60)))).isTrue()
        assertThat(PaymentDocs.addRefund(coll, "pay-81723", Refund("ref-2", 3_000, t0.plusSeconds(90)))).isTrue()
        assertThat(PaymentDocs.addRefund(coll, "pay-81723", Refund("ref-3", 1, t0.plusSeconds(120)))).`as`("1 more than the amount").isFalse()

        val doc = coll.find(Filters.eq("_id", "pay-81723")).first()!!
        assertThat(doc.getLong("refundedMinor")).isEqualTo(4_250)
        assertThat(doc.getList("refunds", Document::class.java).map { it.getString("refundId") }).containsExactly("ref-1", "ref-2")
    }

    @Test
    fun `twenty refunds racing for one payment never refund more than it was worth`() {
        val coll = fresh()
        coll.insertOne(PaymentDocs.toDocument(settled("pay-81724", amount = 10_000)))
        val pool = Executors.newFixedThreadPool(20)
        val start = CountDownLatch(1)
        try {
            val results = (1..20).map { n ->
                pool.submit(Callable {
                    start.await()
                    PaymentDocs.addRefund(coll, "pay-81724", Refund("ref-$n", 1_000, t0.plusSeconds(n.toLong())))
                })
            }
            start.countDown()
            assertThat(results.count { it.get(20, TimeUnit.SECONDS) }).isEqualTo(10)
        } finally {
            pool.shutdownNow()
        }
        val doc = coll.find(Filters.eq("_id", "pay-81724")).first()!!
        assertThat(doc.getLong("refundedMinor")).isEqualTo(10_000)
        assertThat(doc.getList("refunds", Document::class.java)).hasSize(10)
    }

    @Test
    fun `addRefund refuses a payment that isn't settled or doesn't exist`() {
        val coll = fresh()
        coll.insertOne(PaymentDocs.toDocument(settled("pay-81720").copy(status = "FAILED")))
        assertThat(PaymentDocs.addRefund(coll, "pay-81720", Refund("ref-1", 100, t0))).isFalse()
        assertThat(PaymentDocs.addRefund(coll, "pay-99999", Refund("ref-1", 100, t0))).isFalse()
        assertThat(coll.find().first()!!.getList("refunds", Document::class.java)).isEmpty()
    }

    @Test
    fun `the AP3 query walks the compound index and reads exactly what it returns`() {
        val expected = seed.filter { it.merchantId == "M-0042" && it.status == "FAILED" }
            .sortedByDescending { it.createdAt }.take(5).map { it.paymentId }

        val query = PaymentDocs.recentByMerchantStatus(payments, "M-0042", "FAILED", 5)
        assertThat(query.map { it.getString("_id") }.toList()).containsExactlyElementsOf(expected)

        val explain = query.explain(ExplainVerbosity.EXECUTION_STATS)
        val plan = TestMongo.stages(explain["queryPlanner"])
        assertThat(plan).contains("IXSCAN").doesNotContain("COLLSCAN", "SORT")
        assertThat(TestMongo.find(explain["queryPlanner"], "indexName").map { it.getString("indexName") }).contains(PaymentDocs.AP3_INDEX)
        val stats = explain["executionStats"] as Document
        assertThat(stats.getInteger("nReturned")).isEqualTo(5)
        assertThat(stats.getInteger("totalKeysExamined")).isEqualTo(5)
        assertThat(stats.getInteger("totalDocsExamined")).isEqualTo(5)
    }

    @Test
    fun `a refund id finds its payment through a multikey index`() {
        val coll = fresh()
        PaymentDocs.createIndexes(coll)
        coll.insertMany(
            listOf(
                PaymentDocs.toDocument(settled("pay-1", refunds = listOf(Refund("ref-11", 100, t0), Refund("ref-12", 200, t0)))),
                PaymentDocs.toDocument(settled("pay-2", refunds = listOf(Refund("ref-21", 100, t0)))),
                PaymentDocs.toDocument(settled("pay-3")),
            )
        )
        val query = coll.find(Filters.eq("refunds.refundId", "ref-12"))
        assertThat(query.map { it.getString("_id") }.toList()).containsExactly("pay-1")

        val ixscans = TestMongo.find(query.explain(ExplainVerbosity.QUERY_PLANNER)["queryPlanner"], "indexName")
        assertThat(ixscans.map { it.getString("indexName") }).containsExactly(PaymentDocs.REFUND_INDEX)
        assertThat(ixscans.single().getBoolean("isMultiKey")).`as`("one index entry per array element").isTrue()
    }

    @Test
    fun `the daily totals pipeline matches the same totals computed in Kotlin`() {
        val day = LocalDate.of(2026, 11, 7)
        val expected = seed
            .filter { it.merchantId == "M-0042" && it.createdAt.atZone(ZoneOffset.UTC).toLocalDate() == day }
            .groupBy { it.status }
            .map { (status, ps) -> StatusTotal(status, ps.size, ps.sumOf { it.amountMinor }, 0) }
            .sortedBy { it.status }

        val totals = PaymentDocs.dailyTotals(payments, "M-0042", day)

        assertThat(totals).containsExactlyElementsOf(expected)
        assertThat(totals.sumOf { it.count }).isEqualTo(144) // 720 payments that day, every fifth one is M-0042's
        assertThat(PaymentDocs.dailyTotals(payments, "M-0042", day.plusDays(2))).isEmpty()
    }

    @Test
    fun `the daily totals pipeline starts with a match that an index can serve`() {
        val pipeline = PaymentDocs.dailyTotalsPipeline("M-0042", LocalDate.of(2026, 11, 7))
        assertThat(pipeline.first().toBsonDocument().firstKey).isEqualTo("\$match")

        val explain = payments.aggregate(pipeline).explain(ExplainVerbosity.QUERY_PLANNER)
        val stages = TestMongo.stages(explain)
        assertThat(stages).contains("IXSCAN").doesNotContain("COLLSCAN")
    }
}
