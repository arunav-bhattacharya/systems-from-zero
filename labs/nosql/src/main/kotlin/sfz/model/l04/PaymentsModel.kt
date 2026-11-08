package sfz.model.l04

import software.amazon.awssdk.services.dynamodb.model.AttributeValue
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

// The whole payments service in ONE table, keys pk and sk. Each kind of item gets a key prefix,
// and the prefixes are chosen so that sort order answers the questions:
//
//   pk               sk                                          type      found by
//   ACCT#A-1001      LEDGER#2026-11-07T10:00:00.000Z#txf-301     LEDGER    the account's statement
//   ACCT#A-1001      PAY#2026-11-07T10:15:03.120Z#pay-81723      PAYMENT   AP1 (table), AP2 (byPayment), AP3 (byMerchant)
//   ACCT#A-1001      PROFILE                                     ACCOUNT   AP1: sorts right AFTER the payments
//   ACCT#A-1001      REFUND#2026-11-07T11:02:00.000Z#ref-12      REFUND    AP6 (byPayment)
//   IDEMP#9f1c       IDEMP                                       CLAIM     AP4, AP5: "this key was used"
//
// Two global secondary indexes give the same items a second address:
//   byPayment   partition key paymentId, sort key sk               payment, then its refunds
//   byMerchant  partition key merchantId, sort key (status, createdAt) a merchant's payments by status and time
// An item is in an index only if it has the index's key attributes, so byMerchant holds payments only.
//
// Nothing to change in this file.

/** An account: its PROFILE item. Money is in minor units (cents). */
data class Account(val accountId: String, val customerId: String, val currency: String, val balanceMinor: Long)

/** A payment taken from an account for a merchant. */
data class Payment(
    val paymentId: String,
    val accountId: String,
    val merchantId: String,
    val amountMinor: Long,
    val currency: String,
    val status: String,
    val createdAt: Instant,
)

/** A refund of (part of) a payment. */
data class Refund(val refundId: String, val paymentId: String, val accountId: String, val amountMinor: Long, val createdAt: Instant)

/** AP1: what the account screen shows. */
data class AccountView(val account: Account, val payments: List<Payment>)

/** AP2 and AP6 together: a payment and its refunds, oldest refund first. */
data class PaymentWithRefunds(val payment: Payment, val refunds: List<Refund>)

/** AP5: move [amountMinor] from account [from] to account [to]. Retries carry the same [idempotencyKey]. */
data class Transfer(
    val idempotencyKey: String,
    val transferId: String,
    val from: String,
    val to: String,
    val amountMinor: Long,
    val at: Instant,
)

/** What [PaymentsTable.transfer] did. Only [Transferred] changed anything. */
sealed interface TransferResult {
    /** Both balances, both ledger entries and the claim were written, together. */
    data class Transferred(val transferId: String) : TransferResult

    /** The idempotency key was used before, by transfer [transferId]. Nothing was written. */
    data class Replayed(val transferId: String) : TransferResult

    /** The source balance is smaller than the amount. Nothing was written. */
    data object InsufficientFunds : TransferResult

    /** The source or the target account has no PROFILE item. Nothing was written. */
    data object UnknownAccount : TransferResult

    /** Another transaction held one of the items. Nothing was written; retry with the same key. */
    data object Conflict : TransferResult
}

/** Index names, key builders and item conversions shared by the table and the tests. */
object Keys {
    const val BY_PAYMENT = "byPayment"
    const val BY_MERCHANT = "byMerchant"
    const val PROFILE = "PROFILE"
    const val CLAIM = "IDEMP"

    /** Fixed width, always milliseconds, always UTC: text order is time order. */
    private val SORTABLE = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC)

    fun sortable(t: Instant): String = SORTABLE.format(t)
    fun account(accountId: String) = "ACCT#$accountId"
    fun payment(createdAt: Instant, paymentId: String) = "PAY#${sortable(createdAt)}#$paymentId"
    fun refund(createdAt: Instant, refundId: String) = "REFUND#${sortable(createdAt)}#$refundId"
    fun ledger(at: Instant, transferId: String) = "LEDGER#${sortable(at)}#$transferId"
    fun claim(idempotencyKey: String) = "IDEMP#$idempotencyKey"

    /** The full primary key of an item, as the low-level client wants it. */
    fun key(pk: String, sk: String): Map<String, AttributeValue> = mapOf("pk" to s(pk), "sk" to s(sk))

    fun s(v: String): AttributeValue = AttributeValue.fromS(v)
    fun n(v: Long): AttributeValue = AttributeValue.fromN(v.toString())

    fun accountItem(a: Account): Map<String, AttributeValue> = mapOf(
        "pk" to s(account(a.accountId)), "sk" to s(PROFILE), "type" to s("ACCOUNT"),
        "accountId" to s(a.accountId), "customerId" to s(a.customerId),
        "currency" to s(a.currency), "balanceMinor" to n(a.balanceMinor),
    )

    // paymentId, merchantId, status and createdAt put a payment into both indexes
    fun paymentItem(p: Payment): Map<String, AttributeValue> = mapOf(
        "pk" to s(account(p.accountId)), "sk" to s(payment(p.createdAt, p.paymentId)), "type" to s("PAYMENT"),
        "paymentId" to s(p.paymentId), "accountId" to s(p.accountId), "merchantId" to s(p.merchantId),
        "amountMinor" to n(p.amountMinor), "currency" to s(p.currency), "status" to s(p.status),
        "createdAt" to s(sortable(p.createdAt)),
    )

    // paymentId puts a refund into byPayment, next to its payment; no merchantId, so not in byMerchant
    fun refundItem(r: Refund): Map<String, AttributeValue> = mapOf(
        "pk" to s(account(r.accountId)), "sk" to s(refund(r.createdAt, r.refundId)), "type" to s("REFUND"),
        "refundId" to s(r.refundId), "paymentId" to s(r.paymentId), "accountId" to s(r.accountId),
        "amountMinor" to n(r.amountMinor), "createdAt" to s(sortable(r.createdAt)),
    )

    fun toAccount(item: Map<String, AttributeValue>) = Account(
        item.getValue("accountId").s(), item.getValue("customerId").s(),
        item.getValue("currency").s(), item.getValue("balanceMinor").n().toLong(),
    )

    fun toPayment(item: Map<String, AttributeValue>) = Payment(
        item.getValue("paymentId").s(), item.getValue("accountId").s(), item.getValue("merchantId").s(),
        item.getValue("amountMinor").n().toLong(), item.getValue("currency").s(), item.getValue("status").s(),
        Instant.parse(item.getValue("createdAt").s()),
    )

    fun toRefund(item: Map<String, AttributeValue>) = Refund(
        item.getValue("refundId").s(), item.getValue("paymentId").s(), item.getValue("accountId").s(),
        item.getValue("amountMinor").n().toLong(), Instant.parse(item.getValue("createdAt").s()),
    )
}
