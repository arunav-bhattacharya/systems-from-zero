package sfz.nosql.l02

/**
 * The payments service's access patterns, and the keys that must answer them.
 *
 * A payment has: paymentId, accountId, customerId, merchantId, status, amountMinor, currency,
 * createdAt and idempotencyKey.
 */
object PaymentsKeyDesign {
    /** Given: what the service asks, written as queries. Don't change these. */
    val patterns: List<AccessPattern> = listOf(
        // AP1: the account screen shows the latest payments first
        AccessPattern("AP1 account's payments, newest first", equals = setOf("accountId"), orderBy = "createdAt"),
        // AP2: support looks a payment up by its id
        AccessPattern("AP2 payment by id", equals = setOf("paymentId")),
        // AP3: the merchant dashboard lists FAILED (or SETTLED, ...) payments in a time window
        AccessPattern("AP3 merchant's payments by status and time", equals = setOf("merchantId", "status"), range = "createdAt"),
        // AP4: the API checks an idempotency key before it creates a payment
        AccessPattern("AP4 payment by idempotency key", equals = setOf("idempotencyKey")),
    )

    /**
     * The table's primary key first, then one secondary index per pattern the table can't answer.
     * Each index is a copy of the data that every write must also update, so there is no spare one.
     */
    val indexes: List<KeyIndex> = listOf(
        KeyIndex("table", partitionKey = listOf("paymentId")),                             // AP2
        // AP1: one partition per account, payments sorted by time inside it
        KeyIndex("byAccount", partitionKey = listOf("accountId"), sortKey = listOf("createdAt")),
        // AP3: status BEFORE createdAt in the sort key, so "= status" fixes a prefix and the time is the range
        KeyIndex("byMerchantStatus", partitionKey = listOf("merchantId"), sortKey = listOf("status", "createdAt")),
        // AP4: one item per idempotency key
        KeyIndex("byIdempotencyKey", partitionKey = listOf("idempotencyKey")),
    )
}
