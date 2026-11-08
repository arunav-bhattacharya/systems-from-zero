package sfz.model.l04

import sfz.model.l04.Keys.key
import sfz.model.l04.Keys.n
import sfz.model.l04.Keys.s
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.AttributeDefinition
import software.amazon.awssdk.services.dynamodb.model.BillingMode
import software.amazon.awssdk.services.dynamodb.model.GlobalSecondaryIndex
import software.amazon.awssdk.services.dynamodb.model.KeySchemaElement
import software.amazon.awssdk.services.dynamodb.model.KeyType
import software.amazon.awssdk.services.dynamodb.model.Projection
import software.amazon.awssdk.services.dynamodb.model.ProjectionType
import software.amazon.awssdk.services.dynamodb.model.Put
import software.amazon.awssdk.services.dynamodb.model.ReturnValuesOnConditionCheckFailure
import software.amazon.awssdk.services.dynamodb.model.ScalarAttributeType
import software.amazon.awssdk.services.dynamodb.model.TransactWriteItem
import software.amazon.awssdk.services.dynamodb.model.TransactionCanceledException
import software.amazon.awssdk.services.dynamodb.model.Update
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
        val items = ddb.query {
            it.tableName(tableName)
                // one partition, one contiguous run: "PAY#..." < "PROFILE" because 'A' < 'R'
                .keyConditionExpression("pk = :pk AND sk BETWEEN :first AND :last")
                .expressionAttributeValues(mapOf(":pk" to s(Keys.account(accountId)), ":first" to s("PAY#"), ":last" to s(Keys.PROFILE)))
                .scanIndexForward(false) // start at PROFILE, then the newest payment, and walk back in time
                .limit(limit + 1)        // the profile plus `limit` payments, then stop reading
                .consistentRead(true)    // served by the partition's leader: no stale balance
        }.items()
        val profile = items.firstOrNull()?.takeIf { it["sk"]?.s() == Keys.PROFILE } ?: return null
        return AccountView(Keys.toAccount(profile), items.drop(1).map(Keys::toPayment))
    }

    /**
     * AP3: the merchant's payments with one [status] created between [from] and [to] (both
     * inclusive), newest first, at most [limit]. ONE Query on the byMerchant index.
     *
     * `status` is a DynamoDB reserved word: name it through `expressionAttributeNames`.
     */
    fun merchantPayments(merchantId: String, status: String, from: Instant, to: Instant, limit: Int): List<Payment> {
        return ddb.query {
            it.tableName(tableName).indexName(Keys.BY_MERCHANT)
                // equality on the partition key and the first sort attribute, then one range on the next
                .keyConditionExpression("merchantId = :m AND #status = :status AND createdAt BETWEEN :from AND :to")
                .expressionAttributeNames(mapOf("#status" to "status"))
                .expressionAttributeValues(
                    mapOf(
                        ":m" to s(merchantId), ":status" to s(status),
                        ":from" to s(Keys.sortable(from)), ":to" to s(Keys.sortable(to)),
                    )
                )
                .scanIndexForward(false)
                .limit(limit)
        }.items().map(Keys::toPayment)
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
        require(cmd.amountMinor > 0) { "amount must be positive" }
        require(cmd.from != cmd.to) { "a transaction can't touch one item twice" }
        val amount = mapOf(":amt" to n(cmd.amountMinor))
        val actions = listOf(
            // 0. debit, only if the money is there; ALL_OLD returns the balance we failed on
            TransactWriteItem.builder().update(
                Update.builder().tableName(tableName)
                    .key(key(Keys.account(cmd.from), Keys.PROFILE))
                    .updateExpression("SET balanceMinor = balanceMinor - :amt")
                    .conditionExpression("balanceMinor >= :amt")
                    .expressionAttributeValues(amount)
                    .returnValuesOnConditionCheckFailure(ReturnValuesOnConditionCheckFailure.ALL_OLD)
                    .build()
            ).build(),
            // 1. credit, only if the target account exists (an Update would otherwise create it)
            TransactWriteItem.builder().update(
                Update.builder().tableName(tableName)
                    .key(key(Keys.account(cmd.to), Keys.PROFILE))
                    .updateExpression("SET balanceMinor = balanceMinor + :amt")
                    .conditionExpression("attribute_exists(pk)")
                    .expressionAttributeValues(amount)
                    .build()
            ).build(),
            // 2 and 3. one ledger entry in each account's item collection
            ledgerPut(cmd.from, cmd, -cmd.amountMinor, counterparty = cmd.to),
            ledgerPut(cmd.to, cmd, cmd.amountMinor, counterparty = cmd.from),
            // 4. the claim: the same key on every retry, so a second attempt fails here
            TransactWriteItem.builder().put(
                Put.builder().tableName(tableName)
                    .item(key(Keys.claim(cmd.idempotencyKey), Keys.CLAIM) + mapOf("type" to s("CLAIM"), "transferId" to s(cmd.transferId)))
                    .conditionExpression("attribute_not_exists(pk)")
                    .returnValuesOnConditionCheckFailure(ReturnValuesOnConditionCheckFailure.ALL_OLD)
                    .build()
            ).build(),
        )
        try {
            ddb.transactWriteItems { it.transactItems(actions) }
            return TransferResult.Transferred(cmd.transferId)
        } catch (e: TransactionCanceledException) {
            // one reason per action, in the order we sent them; "None" where nothing went wrong
            val reasons = e.cancellationReasons()
            fun failed(i: Int) = reasons.getOrNull(i)?.code() == "ConditionalCheckFailed"
            return when {
                failed(4) -> TransferResult.Replayed(reasons[4].item().getValue("transferId").s())
                failed(0) -> if (reasons[0].item().isNullOrEmpty()) TransferResult.UnknownAccount else TransferResult.InsufficientFunds
                failed(1) -> TransferResult.UnknownAccount
                reasons.any { it.code() == "TransactionConflict" } -> TransferResult.Conflict
                else -> throw e
            }
        }
    }

    private fun ledgerPut(accountId: String, cmd: Transfer, amountMinor: Long, counterparty: String): TransactWriteItem =
        TransactWriteItem.builder().put(
            Put.builder().tableName(tableName)
                .item(
                    key(Keys.account(accountId), Keys.ledger(cmd.at, cmd.transferId)) + mapOf(
                        "type" to s("LEDGER"), "transferId" to s(cmd.transferId),
                        "amountMinor" to n(amountMinor), "counterparty" to s(counterparty),
                        "createdAt" to s(Keys.sortable(cmd.at)),
                    )
                )
                .build()
        ).build()

    /** Reads one item with a strongly consistent GetItem, or null. Given; the tests use it too. */
    fun getItem(pk: String, sk: String) =
        ddb.getItem { it.tableName(tableName).key(key(pk, sk)).consistentRead(true) }.item().takeIf { it.isNotEmpty() }
}
