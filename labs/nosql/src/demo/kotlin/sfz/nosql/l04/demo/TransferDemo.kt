package sfz.nosql.l04.demo

import software.amazon.awssdk.services.dynamodb.model.Put
import software.amazon.awssdk.services.dynamodb.model.TransactWriteItem
import software.amazon.awssdk.services.dynamodb.model.TransactionCanceledException
import software.amazon.awssdk.services.dynamodb.model.Update

/** A transfer as one TransactWriteItems: it all happens, or none of it does. */
fun main() {
    val ddb = localClient()
    val table = "demo-single"
    createPaymentsTable(ddb, table)
    seedPayments(ddb, table) // A-1001 holds 100.00 EUR, A-2002 holds 50.00 EUR

    fun balances() = listOf("A-1001", "A-2002").joinToString(", ") { acct ->
        val item = ddb.getItem { it.tableName(table).key(mapOf("pk" to s("ACCT#$acct"), "sk" to s("PROFILE"))).consistentRead(true) }.item()
        "$acct ${item["balanceMinor"]!!.n()}"
    }
    fun ledgerCount() = ddb.query {
        it.tableName(table).keyConditionExpression("pk = :pk AND begins_with(sk, :l)")
            .expressionAttributeValues(mapOf(":pk" to s("ACCT#A-1001"), ":l" to s("LEDGER#"))).consistentRead(true)
    }.count()

    fun attempt(label: String, key: String, amount: Long) {
        try {
            ddb.transactWriteItems { it.transactItems(transferActions(table, key, "txf-$key", "A-1001", "A-2002", amount)) }
            println("$label: committed")
        } catch (e: TransactionCanceledException) {
            println("$label: ${e.javaClass.simpleName}")
            // one reason per action, in the order they were sent
            val names = listOf("debit A-1001", "credit A-2002", "ledger A-1001", "ledger A-2002", "claim")
            e.cancellationReasons().forEachIndexed { i, r -> println("  [$i] %-14s %s".format(names[i], r.code())) }
        }
        println("  balances: ${balances()}; A-1001 ledger entries: ${ledgerCount()}")
    }

    println("before: ${balances()}; A-1001 ledger entries: ${ledgerCount()}")
    attempt("transfer 30.00 with key k-1", "k-1", 3_000)
    attempt("transfer 500.00 with key k-2", "k-2", 50_000)
    attempt("retry of k-1", "k-1", 3_000)
    ddb.close()
}

/** Debit, credit, two ledger entries and the idempotency claim: five actions, one request. */
fun transferActions(table: String, key: String, transferId: String, from: String, to: String, amount: Long): List<TransactWriteItem> {
    val amt = mapOf(":amt" to n(amount))
    fun ledger(account: String, signed: Long) = TransactWriteItem.builder().put(Put.builder().tableName(table).item(mapOf(
        "pk" to s("ACCT#$account"), "sk" to s("LEDGER#2026-11-07T12:30:00.000Z#$transferId"), "type" to s("LEDGER"),
        "transferId" to s(transferId), "amountMinor" to n(signed),
    )).build()).build()
    return listOf(
        TransactWriteItem.builder().update(Update.builder().tableName(table)
            .key(mapOf("pk" to s("ACCT#$from"), "sk" to s("PROFILE")))
            .updateExpression("SET balanceMinor = balanceMinor - :amt")
            .conditionExpression("balanceMinor >= :amt")      // no overdraft
            .expressionAttributeValues(amt).build()).build(),
        TransactWriteItem.builder().update(Update.builder().tableName(table)
            .key(mapOf("pk" to s("ACCT#$to"), "sk" to s("PROFILE")))
            .updateExpression("SET balanceMinor = balanceMinor + :amt")
            .conditionExpression("attribute_exists(pk)")       // the target account must exist
            .expressionAttributeValues(amt).build()).build(),
        ledger(from, -amount),
        ledger(to, amount),
        TransactWriteItem.builder().put(Put.builder().tableName(table)
            .item(mapOf("pk" to s("IDEMP#$key"), "sk" to s("IDEMP"), "type" to s("CLAIM"), "transferId" to s(transferId)))
            .conditionExpression("attribute_not_exists(pk)")   // first use of this key only
            .build()).build(),
    )
}
