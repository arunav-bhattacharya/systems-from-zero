package sfz.nosql.l03

import software.amazon.awssdk.enhanced.dynamodb.mapper.annotations.DynamoDbBean
import software.amazon.awssdk.enhanced.dynamodb.mapper.annotations.DynamoDbPartitionKey
import software.amazon.awssdk.enhanced.dynamodb.mapper.annotations.DynamoDbSortKey
import java.time.Instant

// Two kinds of item share one table, `payments`. Both use the generic key names pk and sk,
// so the same table can hold accounts, payments, refunds and idempotency claims.
//
//   pk                      sk                                        what
//   ACCT#A-1001             PAY#2026-11-07T10:15:03.120Z#pay-81723    a payment
//   ACCT#A-1001             REFUND#2026-11-07T11:02:00.000Z#ref-12    a refund
//   IDEMP#9f1c-...          IDEMP                                     an idempotency claim
//
// The Enhanced Client maps a Kotlin class through its getters and setters (a "bean"), so these
// are classes with var properties and defaults, not data classes. `@get:` puts the annotation on
// the getter, where the Enhanced Client looks for it. Nothing to change in this file.

/** A payment, stored under its account so one Query returns an account's payments in time order. */
@DynamoDbBean
class PaymentItem {
    /** `ACCT#<accountId>`: the partition key. Every item of one account lands in one partition. */
    @get:DynamoDbPartitionKey
    var pk: String = ""

    /** `PAY#<createdAt>#<paymentId>`: the sort key. Items in a partition are stored in this order. */
    @get:DynamoDbSortKey
    var sk: String = ""

    var paymentId: String = ""
    var accountId: String = ""
    var merchantId: String = ""
    /** Amount in minor units (cents), so no floating point ever touches money. */
    var amountMinor: Long = 0
    var currency: String = ""
    var status: String = ""
    /** Fixed-width UTC timestamp, the same text that sits inside [sk]. */
    var createdAt: String = ""
}

/** "This idempotency key was used for this request." One item per key. */
@DynamoDbBean
class IdempotencyItem {
    /** `IDEMP#<idempotencyKey>` */
    @get:DynamoDbPartitionKey
    var pk: String = ""

    /** Always `IDEMP`: the table has a composite key, so every item needs a sort key. */
    @get:DynamoDbSortKey
    var sk: String = ""

    /** The payment the first request created. A replay returns this id. */
    var paymentId: String = ""
    /** What the first request asked for, so a reuse of the key with a different body is caught. */
    var fingerprint: String = ""
    /** Unix epoch seconds after which the claim is dead. This is the table's TTL attribute. */
    var expiresAt: Long = 0
}

/** A request to take a payment. A client that retries sends the same [idempotencyKey] and [paymentId]. */
data class CreatePayment(
    val idempotencyKey: String,
    val paymentId: String,
    val accountId: String,
    val merchantId: String,
    val amountMinor: Long,
    val currency: String,
    /** When the request arrived. The store uses it as "now". */
    val at: Instant,
) {
    /** What must match for a second request with the same key to count as a retry. */
    fun fingerprint(): String = "$accountId|$merchantId|$amountMinor|$currency"
}

/** What [PaymentStore.createPayment] did. */
sealed interface CreateResult {
    val paymentId: String

    /** First time this key was seen: the payment was written. */
    data class Created(override val paymentId: String) : CreateResult

    /** The key was seen before with the same request: nothing was written, here is the original payment. */
    data class Replayed(override val paymentId: String) : CreateResult

    /** The key was seen before with a DIFFERENT request: refuse it. [paymentId] is the original payment. */
    data class Mismatch(override val paymentId: String) : CreateResult
}
