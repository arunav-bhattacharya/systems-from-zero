package sfz.model.l04

import sfz.model.l04.Keys.key
import sfz.model.l04.Keys.s
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.AttributeDefinition
import software.amazon.awssdk.services.dynamodb.model.BillingMode
import software.amazon.awssdk.services.dynamodb.model.GlobalSecondaryIndex
import software.amazon.awssdk.services.dynamodb.model.KeySchemaElement
import software.amazon.awssdk.services.dynamodb.model.KeyType
import software.amazon.awssdk.services.dynamodb.model.Projection
import software.amazon.awssdk.services.dynamodb.model.ProjectionType
import software.amazon.awssdk.services.dynamodb.model.ScalarAttributeType
import java.time.Instant

/**
 * The payments service in one DynamoDB table, through the low-level client.
 *
 * The low-level client works with `Map<String, AttributeValue>`, which suits a single table:
 * one Query can return items of several types, and the `type` attribute says which is which.
 * See `PaymentsModel.kt` for the keys.
 *
 * Your job: [accountView], [merchantPayments] and [transfer]. Everything else is given.
 */
class PaymentsTable(private val ddb: DynamoDbClient, val tableName: String) {

    /** Creates the table and its two indexes. Given. */
    fun createTable() {
        fun attr(name: String) = AttributeDefinition.builder().attributeName(name).attributeType(ScalarAttributeType.S).build()
        fun hash(name: String) = KeySchemaElement.builder().attributeName(name).keyType(KeyType.HASH).build()
        fun range(name: String) = KeySchemaElement.builder().attributeName(name).keyType(KeyType.RANGE).build()
        val all = Projection.builder().projectionType(ProjectionType.ALL).build()
        ddb.createTable {
            it.tableName(tableName)
                .billingMode(BillingMode.PAY_PER_REQUEST)
                .attributeDefinitions(attr("pk"), attr("sk"), attr("paymentId"), attr("merchantId"), attr("status"), attr("createdAt"))
                .keySchema(hash("pk"), range("sk"))
                .globalSecondaryIndexes(
                    // AP2 + AP6: a payment and its refunds share paymentId; the table's sk orders them
                    GlobalSecondaryIndex.builder().indexName(Keys.BY_PAYMENT)
                        .keySchema(hash("paymentId"), range("sk")).projection(all).build(),
                    // AP3: a multi-attribute sort key (status, then createdAt), no glued strings
                    GlobalSecondaryIndex.builder().indexName(Keys.BY_MERCHANT)
                        .keySchema(hash("merchantId"), range("status"), range("createdAt")).projection(all).build(),
                )
        }
    }

    /** Writes an account's PROFILE item. Given. */
    fun putAccount(a: Account) {
        ddb.putItem { it.tableName(tableName).item(Keys.accountItem(a)) }
    }

    /** Writes a payment item. DynamoDB copies it into both indexes. Given. */
    fun putPayment(p: Payment) {
        ddb.putItem { it.tableName(tableName).item(Keys.paymentItem(p)) }
    }

    /** Writes a refund item. DynamoDB copies it into byPayment. Given. */
    fun putRefund(r: Refund) {
        ddb.putItem { it.tableName(tableName).item(Keys.refundItem(r)) }
    }

    /**
     * AP2 and AP6 in one Query on the byPayment index: the payment, then its refunds oldest first.
     * Given, as a model for the queries you write. Null if there is no such payment.
     */
    fun paymentWithRefunds(paymentId: String): PaymentWithRefunds? {
        val items = ddb.query {
            it.tableName(tableName).indexName(Keys.BY_PAYMENT)
                .keyConditionExpression("paymentId = :id")
                .expressionAttributeValues(mapOf(":id" to s(paymentId)))
        }.items()
        // "PAY#..." sorts before "REFUND#...", so the payment comes first
        val payment = items.firstOrNull { it["type"]?.s() == "PAYMENT" } ?: return null
        return PaymentWithRefunds(Keys.toPayment(payment), items.filter { it["type"]?.s() == "REFUND" }.map(Keys::toRefund))
    }

    /**
     * AP1: the account and its [limit] newest payments, in ONE Query on the table.
     *
     * The account's item collection holds LEDGER#, PAY#, PROFILE and REFUND# items, in that
     * order. Read only the run from `PAY#` to `PROFILE`, backward, so the PROFILE item comes
     * first and the payments follow newest first. Ask for `limit + 1` items. Use a strongly
     * consistent read: the balance must include every transfer that has succeeded.
     * Returns null if the account has no PROFILE item.
     */
    fun accountView(accountId: String, limit: Int): AccountView? {
        TODO("one Query: pk = ACCT#<id> AND sk BETWEEN PAY# AND PROFILE, backward, limit + 1, consistent")
    }

    /**
     * AP3: the merchant's payments with one [status] created between [from] and [to] (both
     * inclusive), newest first, at most [limit]. ONE Query on the byMerchant index.
     *
     * `status` is a DynamoDB reserved word: name it through `expressionAttributeNames`.
     */
    fun merchantPayments(merchantId: String, status: String, from: Instant, to: Instant, limit: Int): List<Payment> {
        TODO("one Query on byMerchant: merchantId = and #status = and createdAt BETWEEN, newest first")
    }

    /**
     * AP5: moves money between two accounts, all or nothing, once per idempotency key.
     *
     * Send ONE `TransactWriteItems` with five actions, in this order:
     * 0. Update the source PROFILE: `SET balanceMinor = balanceMinor - :amt`,
     *    condition `balanceMinor >= :amt`, and `ReturnValuesOnConditionCheckFailure.ALL_OLD`.
     * 1. Update the target PROFILE: `SET balanceMinor = balanceMinor + :amt`, condition `attribute_exists(pk)`.
     * 2. Put the source's ledger item: [Keys.ledger] key, `type` LEDGER, `transferId`,
     *    `amountMinor` = -amount, `counterparty` = the target account id.
     * 3. Put the target's ledger item: the same, with +amount and the source as counterparty.
     * 4. Put the claim: pk [Keys.claim], sk [Keys.CLAIM], `type` CLAIM, `transferId`,
     *    condition `attribute_not_exists(pk)`, and `ReturnValuesOnConditionCheckFailure.ALL_OLD`.
     *
     * If any condition fails, DynamoDB writes nothing and throws `TransactionCanceledException`.
     * Its `cancellationReasons()` has one entry per action, in the same order; a failed condition
     * has code `ConditionalCheckFailed`, and with ALL_OLD its `item()` is the item as it was.
     * Decide in this order: claim failed -> [TransferResult.Replayed] with the claim's transferId;
     * source failed -> [TransferResult.UnknownAccount] if its item is empty, else
     * [TransferResult.InsufficientFunds]; target failed -> [TransferResult.UnknownAccount];
     * any `TransactionConflict` -> [TransferResult.Conflict].
     */
    fun transfer(cmd: Transfer): TransferResult {
        TODO("one TransactWriteItems with five actions; read cancellationReasons() when it is cancelled")
    }

    /** Reads one item with a strongly consistent GetItem, or null. Given; the tests use it too. */
    fun getItem(pk: String, sk: String) =
        ddb.getItem { it.tableName(tableName).key(key(pk, sk)).consistentRead(true) }.item().takeIf { it.isNotEmpty() }
}
