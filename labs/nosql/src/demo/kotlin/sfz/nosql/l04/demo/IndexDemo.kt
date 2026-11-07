package sfz.nosql.l04.demo

import software.amazon.awssdk.services.dynamodb.model.DynamoDbException

/** The same items, read through two global secondary indexes. */
fun main() {
    val ddb = localClient()
    val table = "demo-single"
    createPaymentsTable(ddb, table)
    seedPayments(ddb, table)

    // AP2 + AP6: byPayment is keyed (paymentId; sk), so the payment and its refunds sit together
    println("byPayment, paymentId = pay-81723:")
    ddb.query {
        it.tableName(table).indexName("byPayment")
            .keyConditionExpression("paymentId = :id")
            .expressionAttributeValues(mapOf(":id" to s("pay-81723")))
    }.items().forEach { println("  %-8s %s".format(it["type"]!!.s(), it["sk"]!!.s())) }

    // AP3: byMerchant is keyed (merchantId; status, createdAt): = on status, then a range on createdAt
    println("byMerchant, M-0042, FAILED, 09:00 to 12:00, newest first:")
    ddb.query {
        it.tableName(table).indexName("byMerchant")
            .keyConditionExpression("merchantId = :m AND #status = :st AND createdAt BETWEEN :from AND :to")
            .expressionAttributeNames(mapOf("#status" to "status")) // status is a reserved word
            .expressionAttributeValues(mapOf(
                ":m" to s("M-0042"), ":st" to s("FAILED"),
                ":from" to s("2026-11-07T09:00:00.000Z"), ":to" to s("2026-11-07T12:00:00.000Z"),
            ))
            .scanIndexForward(false)
    }.items().forEach { println("  %s  %s  %s  %s".format(it["createdAt"]!!.s(), it["paymentId"]!!.s(), it["accountId"]!!.s(), it["amountMinor"]!!.n())) }

    // the same, but skip status: the sort key is used left to right, with no gaps
    try {
        ddb.query {
            it.tableName(table).indexName("byMerchant")
                .keyConditionExpression("merchantId = :m AND createdAt > :from")
                .expressionAttributeValues(mapOf(":m" to s("M-0042"), ":from" to s("2026-11-07T09:00:00.000Z")))
        }
    } catch (e: DynamoDbException) {
        println("skip status: ${e.awsErrorDetails().errorMessage()}")
    }

    // an item is in an index only if it has the index's key attributes
    fun count(index: String?) = ddb.scan { r -> r.tableName(table).apply { if (index != null) indexName(index) } }.count()
    println("items: table ${count(null)}, byPayment ${count("byPayment")}, byMerchant ${count("byMerchant")}")
    ddb.close()
}
