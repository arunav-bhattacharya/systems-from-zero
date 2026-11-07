package sfz.nosql.l03

import software.amazon.awssdk.enhanced.dynamodb.DynamoDbEnhancedClient
import software.amazon.awssdk.enhanced.dynamodb.DynamoDbTable
import software.amazon.awssdk.enhanced.dynamodb.TableSchema
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * Payments in one DynamoDB table, written and read with the Enhanced Client.
 *
 * The table has a composite primary key: partition key `pk` and sort key `sk`, both strings.
 * See `PaymentItems.kt` for what goes in them.
 *
 * Your job: [recentPayments] and [createPayment]. Everything else is given.
 */
class PaymentStore(enhanced: DynamoDbEnhancedClient, tableName: String) {
    /** The table seen through the [PaymentItem] schema. */
    val payments: DynamoDbTable<PaymentItem> =
        enhanced.table(tableName, TableSchema.fromBean(PaymentItem::class.java))

    /** The SAME table seen through the [IdempotencyItem] schema. */
    val claims: DynamoDbTable<IdempotencyItem> =
        enhanced.table(tableName, TableSchema.fromBean(IdempotencyItem::class.java))

    /** Creates the table (pk and sk, both strings). Given. */
    fun createTable() {
        payments.createTable()
    }

    /** Writes [item] as-is: a plain PutItem, which replaces any item with the same key. Given. */
    fun save(item: PaymentItem) {
        payments.putItem(item)
    }

    /**
     * Returns up to [limit] payments of [accountId], newest first.
     *
     * Use ONE Query on the account's partition. The partition also holds refunds and other
     * items, so match only sort keys that begin with `PAY#`. Ask DynamoDB for descending order
     * instead of sorting in Kotlin, and stop after [limit] items.
     */
    fun recentPayments(accountId: String, limit: Int): List<PaymentItem> {
        TODO("Query pk = ACCT#<accountId> and begins_with(sk, \"PAY#\"), newest first, at most limit items")
    }

    /**
     * Creates the payment once, however many times the same request arrives.
     *
     * 1. Claim the idempotency key: put an [IdempotencyItem] (`pk = IDEMP#<key>`, `sk = IDEMP`,
     *    the payment id, the request's fingerprint, `expiresAt = at + 24 h` in epoch seconds)
     *    with a condition: the claim must not exist yet, OR the existing claim has expired
     *    (`expiresAt < now`). TTL deletes expired items lazily, so an expired claim may still be there.
     * 2. If the put succeeds, write the payment ([toItem]) and return [CreateResult.Created].
     * 3. If the condition fails, DynamoDB throws `ConditionalCheckFailedException`. Read the
     *    existing claim with a strongly consistent read. Same fingerprint: return
     *    [CreateResult.Replayed] with the claim's payment id. Different: [CreateResult.Mismatch].
     */
    fun createPayment(cmd: CreatePayment): CreateResult {
        TODO("conditional put of the claim, then the payment; on ConditionalCheckFailedException read the claim")
    }

    companion object {
        /** How long a claim protects its key. */
        const val CLAIM_TTL_SECONDS = 24 * 60 * 60L

        /**
         * Fixed width, always with milliseconds, always UTC, so text order is time order.
         * (`Instant.toString()` drops zero millis, and "03Z" sorts AFTER "03.120Z".)
         */
        private val SORTABLE = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC)

        fun sortableTime(t: Instant): String = SORTABLE.format(t)
        fun accountKey(accountId: String): String = "ACCT#$accountId"
        fun paymentSortKey(createdAt: Instant, paymentId: String): String = "PAY#${sortableTime(createdAt)}#$paymentId"
        fun claimKey(idempotencyKey: String): String = "IDEMP#$idempotencyKey"
        const val CLAIM_SORT_KEY = "IDEMP"

        /** The payment item for a request. Given. */
        fun toItem(cmd: CreatePayment): PaymentItem = PaymentItem().apply {
            pk = accountKey(cmd.accountId)
            sk = paymentSortKey(cmd.at, cmd.paymentId)
            paymentId = cmd.paymentId
            accountId = cmd.accountId
            merchantId = cmd.merchantId
            amountMinor = cmd.amountMinor
            currency = cmd.currency
            status = "AUTHORIZED"
            createdAt = sortableTime(cmd.at)
        }
    }
}
