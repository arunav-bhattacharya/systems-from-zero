package sfz.model.l04.demo

import software.amazon.awssdk.services.dynamodb.model.QueryResponse

/** One item collection holds an account, its payments, refunds and ledger. Which Query returns the account screen? */
fun main() {
    val ddb = localClient()
    val table = "demo-single"
    createPaymentsTable(ddb, table)
    seedPayments(ddb, table) // 12 items, written in no particular order (see DemoTable.kt)

    fun show(title: String, r: QueryResponse) {
        println("$title  (read ${r.scannedCount()}, returned ${r.count()})")
        r.items().forEach { println("  %-44s %s".format(it["sk"]!!.s(), it["type"]!!.s())) }
    }

    // 1. the whole item collection: DynamoDB keeps it sorted by sk, byte by byte
    show("pk = ACCT#A-1001, forward:", ddb.query {
        it.tableName(table)
            .keyConditionExpression("pk = :pk")
            .expressionAttributeValues(mapOf(":pk" to s("ACCT#A-1001")))
    })

    // 2. backward from the end, 4 items: the refunds sort last, so they come first
    show("backward, Limit 4, no condition on sk:", ddb.query {
        it.tableName(table)
            .keyConditionExpression("pk = :pk")
            .expressionAttributeValues(mapOf(":pk" to s("ACCT#A-1001")))
            .scanIndexForward(false).limit(4)
    })

    // 3. the account screen: only the run from PAY# to PROFILE, backward: profile, then newest payments
    show("backward, sk BETWEEN PAY# AND PROFILE, Limit 4:", ddb.query {
        it.tableName(table)
            .keyConditionExpression("pk = :pk AND sk BETWEEN :first AND :last")
            .expressionAttributeValues(mapOf(":pk" to s("ACCT#A-1001"), ":first" to s("PAY#"), ":last" to s("PROFILE")))
            .scanIndexForward(false).limit(4)
    })
    ddb.close()
}
