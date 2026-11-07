package sfz.nosql.l03.demo

import software.amazon.awssdk.auth.credentials.AwsBasicCredentials
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.AttributeDefinition
import software.amazon.awssdk.services.dynamodb.model.AttributeValue
import software.amazon.awssdk.services.dynamodb.model.BillingMode
import software.amazon.awssdk.services.dynamodb.model.KeySchemaElement
import software.amazon.awssdk.services.dynamodb.model.KeyType
import software.amazon.awssdk.services.dynamodb.model.PutRequest
import software.amazon.awssdk.services.dynamodb.model.ReturnConsumedCapacity
import software.amazon.awssdk.services.dynamodb.model.ScalarAttributeType
import software.amazon.awssdk.services.dynamodb.model.WriteRequest
import java.net.URI
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/** 2,000 payments for 100 accounts. Three ways to find one account's payments, and what each one reads. */
fun main() {
    val ddb = DynamoDbClient.builder()
        .endpointOverride(URI.create("http://localhost:8000"))
        .region(Region.US_EAST_1)
        .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("sfz", "sfz")))
        .build()
    val table = "demo-query-cost"
    runCatching { ddb.deleteTable { it.tableName(table) } }
    ddb.createTable {
        it.tableName(table)
            .attributeDefinitions(
                AttributeDefinition.builder().attributeName("pk").attributeType(ScalarAttributeType.S).build(),
                AttributeDefinition.builder().attributeName("sk").attributeType(ScalarAttributeType.S).build(),
            )
            .keySchema(
                KeySchemaElement.builder().attributeName("pk").keyType(KeyType.HASH).build(),
                KeySchemaElement.builder().attributeName("sk").keyType(KeyType.RANGE).build(),
            )
            .billingMode(BillingMode.PAY_PER_REQUEST)
    }

    // seed: account A-0000 .. A-0099, 20 payments each, amounts 500..10,000 cents
    val fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC)
    val start = Instant.parse("2026-11-01T00:00:00Z")
    val items = (0 until 2_000).map { i ->
        val account = "A-%04d".format(i % 100)
        val at = fmt.format(start.plusSeconds(i * 157L))
        mapOf(
            "pk" to s("ACCT#$account"), "sk" to s("PAY#$at#pay-$i"),
            "accountId" to s(account), "amountMinor" to n(500L + (i * 7919L) % 9_501),
        )
    }
    items.chunked(25).forEach { batch -> // BatchWriteItem takes at most 25 items
        ddb.batchWriteItem { it.requestItems(mapOf(table to batch.map { item ->
            WriteRequest.builder().putRequest(PutRequest.builder().item(item).build()).build()
        })) }
    }

    // A. Query: one partition, one range, read from the end
    val a = ddb.query {
        it.tableName(table)
            .keyConditionExpression("pk = :pk AND begins_with(sk, :pay)")
            .expressionAttributeValues(mapOf(":pk" to s("ACCT#A-0042"), ":pay" to s("PAY#")))
            .scanIndexForward(false).limit(5)
            .returnConsumedCapacity(ReturnConsumedCapacity.TOTAL)
    }
    println("A. Query, newest 5:          returned %4d, read %4d, capacity units %s".format(a.count(), a.scannedCount(), a.consumedCapacity()?.capacityUnits()))
    a.items().take(2).forEach { println("     ${it["sk"]!!.s()}") }

    // B. Query plus a filter: the filter runs AFTER the read
    val b = ddb.query {
        it.tableName(table)
            .keyConditionExpression("pk = :pk")
            .filterExpression("amountMinor > :big")
            .expressionAttributeValues(mapOf(":pk" to s("ACCT#A-0042"), ":big" to n(8_000)))
            .returnConsumedCapacity(ReturnConsumedCapacity.TOTAL)
    }
    println("B. Query + filter > 80.00:   returned %4d, read %4d, capacity units %s".format(b.count(), b.scannedCount(), b.consumedCapacity()?.capacityUnits()))

    // C. Scan with a filter on a non-key attribute: reads the whole table to find 20 items
    val c = ddb.scanPaginator {
        it.tableName(table)
            .filterExpression("accountId = :acct")
            .expressionAttributeValues(mapOf(":acct" to s("A-0042")))
            .returnConsumedCapacity(ReturnConsumedCapacity.TOTAL)
    }.toList()
    println("C. Scan + filter on account: returned %4d, read %4d, capacity units %s".format(
        c.sumOf { it.count() }, c.sumOf { it.scannedCount() }, c.sumOf { it.consumedCapacity()?.capacityUnits() ?: 0.0 }))
    ddb.close()
}

private fun s(v: String): AttributeValue = AttributeValue.fromS(v)
private fun n(v: Long): AttributeValue = AttributeValue.fromN(v.toString())
