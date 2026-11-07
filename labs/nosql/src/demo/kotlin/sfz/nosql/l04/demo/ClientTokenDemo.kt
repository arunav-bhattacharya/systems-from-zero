package sfz.nosql.l04.demo

import software.amazon.awssdk.services.dynamodb.model.IdempotentParameterMismatchException
import java.util.UUID

/** The request-level guard: a ClientRequestToken makes a repeated TransactWriteItems a no-op for 10 minutes. */
fun main() {
    val ddb = localClient()
    val table = "demo-single"
    createPaymentsTable(ddb, table)
    seedPayments(ddb, table) // A-1001 holds 100.00 EUR, A-2002 holds 50.00 EUR

    fun balance() = ddb.getItem {
        it.tableName(table).key(mapOf("pk" to s("ACCT#A-1001"), "sk" to s("PROFILE"))).consistentRead(true)
    }.item()["balanceMinor"]!!.n()

    // at most 36 characters; a fresh one per run, because DynamoDB remembers a token
    // for 10 minutes after the request that used it finishes
    val token = UUID.randomUUID().toString()
    fun send(key: String, amount: Long) = ddb.transactWriteItems {
        it.transactItems(transferActions(table, key, "txf-$key", "A-1001", "A-2002", amount))
            .clientRequestToken(token)
    }

    send("k-7", 3_000)
    println("first call with the token:        A-1001 = ${balance()}")
    send("k-7", 3_000) // say the response was lost and the caller sends the identical request again
    println("same request, same token again:   A-1001 = ${balance()}  (success, nothing written)")
    try {
        send("k-7", 4_000)
    } catch (e: IdempotentParameterMismatchException) {
        println("same token, amount 40.00:         ${e.javaClass.simpleName}")
    }
    ddb.close()
}
