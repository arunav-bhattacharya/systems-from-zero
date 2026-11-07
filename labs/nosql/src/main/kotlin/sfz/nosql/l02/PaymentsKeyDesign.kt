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
     * YOUR DESIGN: the table's primary key first, then any secondary indexes.
     *
     * Right now only AP2 is answered without a scan. Add indexes until every pattern is a
     * KEY_LOOKUP or a RANGE_READ. Each index you add is a copy of the data that every write
     * must also update, so add no more than the patterns need.
     */
    val indexes: List<KeyIndex> = listOf(
        KeyIndex("table", partitionKey = listOf("paymentId")),
    )
}
