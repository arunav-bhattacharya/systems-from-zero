package sfz.nosql.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import sfz.nosql.support.TestDynamoDb
import software.amazon.awssdk.services.dynamodb.model.AttributeValue
import software.amazon.awssdk.services.dynamodb.model.QueryRequest
import java.time.Duration
import java.time.Instant
import java.util.concurrent.Callable
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class PaymentStoreTest {
    private lateinit var table: String
    private lateinit var store: PaymentStore
    private val t0: Instant = Instant.parse("2026-11-07T10:00:00Z")

    @BeforeEach
    fun freshTable() {
        // every test gets its own table, so tests never see each other's items
        table = TestDynamoDb.uniqueTableName("payments")
        store = PaymentStore(TestDynamoDb.enhanced, table)
        store.createTable()
    }

    private fun payment(account: String, id: String, at: Instant, amount: Long = 1_000) =
        PaymentStore.toItem(CreatePayment("k-$id", id, account, "M-0042", amount, "EUR", at))

    private fun request(key: String = "idem-1", id: String = "pay-1", amount: Long = 4_250, at: Instant = t0) =
        CreatePayment(key, id, "A-1001", "M-0042", amount, "EUR", at)

    /** Raw items of one partition, read with the low-level client so these tests don't depend on recentPayments. */
    private fun rawPartition(pk: String): List<Map<String, AttributeValue>> =
        TestDynamoDb.client.query(
            QueryRequest.builder().tableName(table)
                .keyConditionExpression("pk = :pk")
                .expressionAttributeValues(mapOf(":pk" to AttributeValue.fromS(pk)))
                .consistentRead(true)
                .build()
        ).items()

    @Test
    fun `recentPayments returns only this account's payments, newest first, at most limit`() {
        // written out of time order on purpose: the sort key orders them, not the insert order
        for (minute in listOf(5L, 1L, 9L, 3L, 7L, 2L)) {
            store.save(payment("A-1001", "pay-$minute", t0.plusSeconds(minute * 60)))
        }
        // a refund in the same partition: its sort key "REFUND#..." sorts AFTER every "PAY#..."
        store.save(PaymentItem().apply { pk = "ACCT#A-1001"; sk = "REFUND#2026-11-07T11:00:00.000Z#ref-1" })
        // another account's payments, newer than all of A-1001's
        store.save(payment("A-2002", "pay-other", t0.plusSeconds(3_600)))

        val recent = store.recentPayments("A-1001", 4)

        assertThat(recent.map { it.paymentId }).containsExactly("pay-9", "pay-7", "pay-5", "pay-3")
        assertThat(recent).allSatisfy { assertThat(it.accountId).isEqualTo("A-1001") }
    }

    @Test
    fun `recentPayments of an account with no payments is empty`() {
        store.save(PaymentItem().apply { pk = "ACCT#A-3003"; sk = "REFUND#2026-11-07T11:00:00.000Z#ref-9" })
        assertThat(store.recentPayments("A-3003", 10)).isEmpty()
        assertThat(store.recentPayments("A-4004", 10)).isEmpty()
    }

    @Test
    fun `createPayment writes the payment and a claim that expires 24 hours later`() {
        val result = store.createPayment(request())

        assertThat(result).isEqualTo(CreateResult.Created("pay-1"))
        val payments = rawPartition("ACCT#A-1001")
        assertThat(payments).hasSize(1)
        assertThat(payments[0]["sk"]!!.s()).isEqualTo("PAY#2026-11-07T10:00:00.000Z#pay-1")
        val claim = rawPartition("IDEMP#idem-1").single()
        assertThat(claim["sk"]!!.s()).isEqualTo("IDEMP")
        assertThat(claim["paymentId"]!!.s()).isEqualTo("pay-1")
        // TTL needs a Number holding Unix epoch SECONDS
        assertThat(claim["expiresAt"]!!.n()).isEqualTo((t0.epochSecond + 86_400).toString())
    }

    @Test
    fun `a retry with the same key and body is Replayed and writes nothing new`() {
        store.createPayment(request())
        // the retry arrives 3 seconds later, so a key built from the arrival time would differ
        val retry = store.createPayment(request(id = "pay-1-retry", at = t0.plusSeconds(3)))

        assertThat(retry).isEqualTo(CreateResult.Replayed("pay-1"))
        assertThat(rawPartition("ACCT#A-1001")).hasSize(1)
    }

    @Test
    fun `the same key with a different amount is a Mismatch`() {
        store.createPayment(request(amount = 4_250))
        val other = store.createPayment(request(id = "pay-2", amount = 9_900, at = t0.plusSeconds(10)))

        assertThat(other).isEqualTo(CreateResult.Mismatch("pay-1"))
        assertThat(rawPartition("ACCT#A-1001")).hasSize(1)
    }

    @Test
    @Timeout(30)
    fun `eight concurrent deliveries of one request create exactly one payment`() {
        val threads = 8
        val ready = CountDownLatch(threads)
        val go = CountDownLatch(1)
        val pool = Executors.newFixedThreadPool(threads)
        try {
            val futures = (1..threads).map { n ->
                pool.submit(Callable {
                    ready.countDown()
                    go.await()
                    // same key and body, different payment ids: only the winner's id may survive
                    store.createPayment(request(id = "pay-from-consumer-$n"))
                })
            }
            ready.await()
            go.countDown()
            val results = futures.map { it.get(20, TimeUnit.SECONDS) }

            assertThat(results.filterIsInstance<CreateResult.Created>()).hasSize(1)
            assertThat(results.filterIsInstance<CreateResult.Replayed>()).hasSize(threads - 1)
            assertThat(results.map { it.paymentId }.toSet()).hasSize(1)
            assertThat(rawPartition("ACCT#A-1001")).hasSize(1)
        } finally {
            pool.shutdownNow()
        }
    }

    @Test
    fun `an expired claim no longer blocks the key, even before TTL deletes it`() {
        store.createPayment(request(amount = 4_250))
        // 25 hours later the claim has expired but is still in the table: TTL deletes lazily
        val later = t0.plus(Duration.ofHours(25))
        val reused = store.createPayment(request(id = "pay-2", amount = 9_900, at = later))

        assertThat(reused).isEqualTo(CreateResult.Created("pay-2"))
        assertThat(rawPartition("ACCT#A-1001")).hasSize(2)
        assertThat(rawPartition("IDEMP#idem-1").single()["paymentId"]!!.s()).isEqualTo("pay-2")
    }
}
