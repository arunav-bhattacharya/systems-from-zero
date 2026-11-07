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
import software.amazon.awssdk.services.dynamodb.model.ScalarAttributeType
import java.net.URI

/** Five items, two partitions: watch DynamoDB keep one account's items together, sorted by sk. */
fun main() {
    // DynamoDB Local from env/dynamodb.yml; it accepts any credentials and Region
    val ddb = DynamoDbClient.builder()
        .endpointOverride(URI.create("http://localhost:8000"))
        .region(Region.US_EAST_1)
        .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("sfz", "sfz")))
        .build()
    val table = "demo-items"

    // 1. a table is a name plus a key schema: pk (partition key) and sk (sort key), both strings
    runCatching { ddb.deleteTable { it.tableName(table) } } // start clean on every run
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

    // 2. write five items, deliberately NOT in sort-key order. Only pk and sk are declared;
    //    every other attribute is whatever this item carries.
    fun put(pk: String, sk: String, vararg attrs: Pair<String, AttributeValue>) =
        ddb.putItem { it.tableName(table).item(mapOf("pk" to s(pk), "sk" to s(sk)) + attrs) }
    put("ACCT#A-1001", "PAY#2026-11-07T10:15:03.120Z#pay-81723", "amountMinor" to n(4250))
    put("ACCT#A-1001", "META", "customerId" to s("C-77"), "currency" to s("EUR"))
    put("ACCT#A-1001", "REFUND#2026-11-07T11:02:00.000Z#ref-12", "amountMinor" to n(1000))
    put("ACCT#A-1001", "PAY#2026-11-06T18:40:51.004Z#pay-80911", "amountMinor" to n(1999))
    put("ACCT#A-2002", "META", "customerId" to s("C-91"), "currency" to s("GBP"))

    // 3. one Query with only the partition key returns the whole item collection, in sk order
    println("Query pk = ACCT#A-1001:")
    ddb.query {
        it.tableName(table)
            .keyConditionExpression("pk = :pk")
            .expressionAttributeValues(mapOf(":pk" to s("ACCT#A-1001")))
    }.items().forEach { println("  ${it["sk"]!!.s()}") }

    // 4. GetItem needs the FULL primary key: partition key and sort key
    val meta = ddb.getItem { it.tableName(table).key(mapOf("pk" to s("ACCT#A-1001"), "sk" to s("META"))) }.item()
    println("GetItem (ACCT#A-1001, META): $meta")
    ddb.close()
}

private fun s(v: String): AttributeValue = AttributeValue.fromS(v)
private fun n(v: Long): AttributeValue = AttributeValue.fromN(v.toString())
