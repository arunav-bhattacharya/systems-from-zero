package sfz.model.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import sfz.nosql.support.RequestLog
import sfz.nosql.support.TestDynamoDb
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.AttributeValue
import software.amazon.awssdk.services.dynamodb.model.QueryRequest
import java.time.Instant
import java.util.concurrent.Callable
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class PaymentsTableTest {
    private val log = RequestLog()
    private lateinit var client: DynamoDbClient
    private lateinit var table: PaymentsTable
    private val t0: Instant = Instant.parse("2026-11-07T08:00:00Z")

    @BeforeEach
    fun freshTable() {
        // every test gets its own table, and a client that records what it sends
        client = TestDynamoDb.clientWith(log)
        table = PaymentsTable(client, TestDynamoDb.uniqueTableName("single"))
        table.createTable()
        table.putAccount(Account("A-1001", "C-77", "EUR", 10_000))
        table.putAccount(Account("A-2002", "C-91", "EUR", 5_000))
        log.clear()
    }

    @AfterEach
    fun closeClient() = client.close()

    private fun at(minutes: Long): Instant = t0.plusSeconds(minutes * 60)

    private fun payment(id: String, minutes: Long, account: String = "A-1001", merchant: String = "M-0042", status: String = "SETTLED") =
        Payment(id, account, merchant, 1_000 + minutes, "EUR", status, at(minutes))

    private fun transfer(key: String, amount: Long, from: String = "A-1001", to: String = "A-2002", id: String = "txf-$key") =
        Transfer(key, id, from, to, amount, at(30))

    private fun balance(accountId: String): Long =
        table.getItem(Keys.account(accountId), Keys.PROFILE)!!.getValue("balanceMinor").n().toLong()

    /** Every item of one partition, read raw with the shared client, so these checks don't depend on your code. */
    private fun partition(pk: String): List<Map<String, AttributeValue>> =
        TestDynamoDb.client.query(
            QueryRequest.builder().tableName(table.tableName)
                .keyConditionExpression("pk = :pk")
                .expressionAttributeValues(mapOf(":pk" to AttributeValue.fromS(pk)))
                .consistentRead(true).build()
        ).items()

    private fun ledger(accountId: String) = partition(Keys.account(accountId)).filter { it["type"]?.s() == "LEDGER" }

    /** A ledger entry written raw, so the read tests don't depend on your transfer. */
    private fun putLedger(accountId: String, transferId: String, minutes: Long) {
        TestDynamoDb.client.putItem {
            it.tableName(table.tableName).item(
                Keys.key(Keys.account(accountId), Keys.ledger(at(minutes), transferId)) +
                    mapOf("type" to Keys.s("LEDGER"), "transferId" to Keys.s(transferId), "amountMinor" to Keys.n(-100))
            )
        }
    }

    @Test
    fun `accountView returns the profile and the newest payments with one Query`() {
        // written out of time order; the sort key orders them
        for (m in listOf(5L, 1L, 9L, 3L, 7L)) table.putPayment(payment("pay-$m", m))
        // neighbours in the same item collection that must NOT come back
        table.putRefund(Refund("ref-1", "pay-9", "A-1001", 500, at(60)))
        putLedger("A-1001", "txf-0", 4)
        table.putPayment(payment("pay-other", 99, account = "A-2002"))
        log.clear()

        val view = table.accountView("A-1001", 3)!!

        assertThat(view.account.balanceMinor).isEqualTo(10_000)
        assertThat(view.payments.map { it.paymentId }).containsExactly("pay-9", "pay-7", "pay-5")
        assertThat(log.names).containsExactly("QueryRequest")
        val q = log.requests.single() as QueryRequest
        assertThat(q.indexName()).isNull()
        assertThat(q.consistentRead()).isTrue()
    }

    @Test
    fun `accountView of an account without payments, and of no account at all`() {
        putLedger("A-1001", "txf-0", 4) // a ledger entry, but no payments
        assertThat(table.accountView("A-1001", 5)!!.payments).isEmpty()
        assertThat(table.accountView("A-1001", 5)!!.account.customerId).isEqualTo("C-77")
        assertThat(table.accountView("A-9999", 5)).isNull()
    }

    @Test
    fun `merchantPayments reads one status in a time window, newest first, from the byMerchant index`() {
        table.putPayment(payment("pay-1", 50, status = "FAILED"))   // before the window
        table.putPayment(payment("pay-2", 70, status = "FAILED"))
        table.putPayment(payment("pay-3", 80, status = "SETTLED"))  // wrong status
        table.putPayment(payment("pay-4", 90, status = "FAILED", account = "A-2002"))
        table.putPayment(payment("pay-5", 100, status = "FAILED", merchant = "M-0043")) // other merchant
        table.putPayment(payment("pay-6", 120, status = "FAILED"))  // the window's last minute: inclusive
        table.putPayment(payment("pay-7", 130, status = "FAILED"))  // after the window
        log.clear()

        val failed = table.merchantPayments("M-0042", "FAILED", at(60), at(120), 10)

        assertThat(failed.map { it.paymentId }).containsExactly("pay-6", "pay-4", "pay-2")
        assertThat(table.merchantPayments("M-0042", "FAILED", at(60), at(120), 2).map { it.paymentId })
            .containsExactly("pay-6", "pay-4")
        assertThat(log.names).containsOnly("QueryRequest")
        assertThat(log.requests.map { (it as QueryRequest).indexName() }).containsOnly(Keys.BY_MERCHANT)
    }

    @Test
    fun `paymentWithRefunds reads a payment and its refunds from the byPayment index (given)`() {
        table.putPayment(payment("pay-81723", 10))
        table.putRefund(Refund("ref-2", "pay-81723", "A-1001", 300, at(40)))
        table.putRefund(Refund("ref-1", "pay-81723", "A-1001", 200, at(20)))
        val pr = table.paymentWithRefunds("pay-81723")!!
        assertThat(pr.payment.amountMinor).isEqualTo(1_010)
        assertThat(pr.refunds.map { it.refundId }).containsExactly("ref-1", "ref-2")
    }

    @Test
    fun `transfer moves the money and writes a ledger entry on each side and a claim`() {
        val result = table.transfer(transfer("k-1", 3_000))
        val sent = log.names

        assertThat(result).isEqualTo(TransferResult.Transferred("txf-k-1"))
        assertThat(sent).containsExactly("TransactWriteItemsRequest")
        assertThat(balance("A-1001")).isEqualTo(7_000)
        assertThat(balance("A-2002")).isEqualTo(8_000)
        assertThat(ledger("A-1001").map { it.getValue("amountMinor").n() }).containsExactly("-3000")
        assertThat(ledger("A-2002").map { it.getValue("amountMinor").n() }).containsExactly("3000")
        assertThat(ledger("A-1001").single().getValue("sk").s()).isEqualTo("LEDGER#2026-11-07T08:30:00.000Z#txf-k-1")
        assertThat(table.getItem(Keys.claim("k-1"), Keys.CLAIM)!!.getValue("transferId").s()).isEqualTo("txf-k-1")
    }

    @Test
    fun `a transfer that would overdraw writes nothing at all`() {
        val result = table.transfer(transfer("k-2", 10_001))

        assertThat(result).isEqualTo(TransferResult.InsufficientFunds)
        assertThat(balance("A-1001")).isEqualTo(10_000)
        assertThat(balance("A-2002")).isEqualTo(5_000)
        assertThat(ledger("A-1001")).isEmpty()
        assertThat(ledger("A-2002")).isEmpty()
        // the claim was the last action, and it is gone too: all or nothing
        assertThat(table.getItem(Keys.claim("k-2"), Keys.CLAIM)).isNull()
    }

    @Test
    fun `a transfer from or to an unknown account writes nothing`() {
        assertThat(table.transfer(transfer("k-3", 100, to = "A-9999"))).isEqualTo(TransferResult.UnknownAccount)
        assertThat(table.transfer(transfer("k-4", 100, from = "A-9999"))).isEqualTo(TransferResult.UnknownAccount)
        assertThat(balance("A-1001")).isEqualTo(10_000)
        assertThat(table.getItem(Keys.account("A-9999"), Keys.PROFILE)).isNull()
        assertThat(ledger("A-1001")).isEmpty()
    }

    @Test
    fun `a retried transfer with the same idempotency key moves the money once`() {
        table.transfer(transfer("k-5", 2_500))
        // the client timed out and retries: same key, but it built a new transfer id
        val retry = table.transfer(transfer("k-5", 2_500, id = "txf-retry"))

        assertThat(retry).isEqualTo(TransferResult.Replayed("txf-k-5"))
        assertThat(balance("A-1001")).isEqualTo(7_500)
        assertThat(balance("A-2002")).isEqualTo(7_500)
        assertThat(ledger("A-1001")).hasSize(1)
    }

    @Test
    @Timeout(30)
    fun `concurrent transfers never overdraw and never lose money`() {
        val threads = 8
        val ready = CountDownLatch(threads)
        val go = CountDownLatch(1)
        val pool = Executors.newFixedThreadPool(threads)
        try {
            // eight transfers of 30.00 from 100.00: at most three can succeed
            val futures = (1..threads).map { n ->
                pool.submit(Callable {
                    ready.countDown()
                    go.await()
                    table.transfer(transfer("race-$n", 3_000))
                })
            }
            ready.await()
            go.countDown()
            val results = futures.map { it.get(20, TimeUnit.SECONDS) }
            val done = results.count { it is TransferResult.Transferred }

            assertThat(done).isBetween(1, 3)
            assertThat(results).allMatch { it is TransferResult.Transferred || it == TransferResult.InsufficientFunds || it == TransferResult.Conflict }
            assertThat(balance("A-1001")).isEqualTo(10_000L - 3_000L * done).isNotNegative()
            assertThat(balance("A-1001") + balance("A-2002")).isEqualTo(15_000)
            assertThat(ledger("A-1001")).hasSize(done)
            assertThat(ledger("A-2002")).hasSize(done)
        } finally {
            pool.shutdownNow()
        }
    }
}
