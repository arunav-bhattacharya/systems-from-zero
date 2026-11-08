package sfz.model.l03.demo

import software.amazon.awssdk.auth.credentials.AwsBasicCredentials
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider
import software.amazon.awssdk.enhanced.dynamodb.DynamoDbEnhancedClient
import software.amazon.awssdk.enhanced.dynamodb.Expression
import software.amazon.awssdk.enhanced.dynamodb.Key
import software.amazon.awssdk.enhanced.dynamodb.TableSchema
import software.amazon.awssdk.enhanced.dynamodb.mapper.annotations.DynamoDbBean
import software.amazon.awssdk.enhanced.dynamodb.mapper.annotations.DynamoDbPartitionKey
import software.amazon.awssdk.enhanced.dynamodb.mapper.annotations.DynamoDbSortKey
import software.amazon.awssdk.enhanced.dynamodb.model.PutItemEnhancedRequest
import software.amazon.awssdk.enhanced.dynamodb.model.QueryConditional
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.ConditionalCheckFailedException
import java.net.URI

/** A Kotlin class the Enhanced Client can map: var properties with defaults, key annotations on the getters. */
@DynamoDbBean
class DemoPayment {
    @get:DynamoDbPartitionKey
    var pk: String = ""

    @get:DynamoDbSortKey
    var sk: String = ""

    var amountMinor: Long = 0
}

/** Three ways to write "the same" payment twice. Only one of them notices. */
fun main() {
    val low = DynamoDbClient.builder()
        .endpointOverride(URI.create("http://localhost:8000"))
        .region(Region.US_EAST_1)
        .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("sfz", "sfz")))
        .build()
    val enhanced = DynamoDbEnhancedClient.builder().dynamoDbClient(low).build()
    val table = enhanced.table("demo-conditional", TableSchema.fromBean(DemoPayment::class.java))
    runCatching { table.deleteTable() } // start clean on every run
    table.createTable()

    fun payment(pk: String, sk: String, amount: Long) =
        DemoPayment().apply { this.pk = pk; this.sk = sk; amountMinor = amount }
    val key = Key.builder().partitionValue("ACCT#A-1001").sortValue("PAY#pay-81723").build()

    // 1. plain PutItem twice with the same key: the second silently replaces the first
    table.putItem(payment("ACCT#A-1001", "PAY#pay-81723", 4250))
    table.putItem(payment("ACCT#A-1001", "PAY#pay-81723", 9900))
    println("1. plain put twice: no error, amountMinor is now ${table.getItem(key).amountMinor}")

    // 2. the same write with a condition: only if no item with this key exists yet
    val mustBeNew = Expression.builder().expression("attribute_not_exists(pk)").build()
    fun putIfNew(item: DemoPayment) = table.putItem(
        PutItemEnhancedRequest.builder(DemoPayment::class.java).item(item).conditionExpression(mustBeNew).build()
    )
    putIfNew(payment("ACCT#A-1001", "PAY#pay-90001", 4250))
    println("2. conditional put of pay-90001: written")
    try {
        putIfNew(payment("ACCT#A-1001", "PAY#pay-90001", 4250))
    } catch (e: ConditionalCheckFailedException) {
        println("   again: ${e.javaClass.simpleName}: ${e.awsErrorDetails().errorMessage()}")
    }

    // 3. the trap: the sort key contains the ARRIVAL time, and the retry arrives 3 seconds later
    putIfNew(payment("ACCT#A-2002", "PAY#2026-11-07T10:15:03.120Z", 4250))
    putIfNew(payment("ACCT#A-2002", "PAY#2026-11-07T10:15:06.480Z", 4250))
    val copies = table.query(QueryConditional.keyEqualTo(Key.builder().partitionValue("ACCT#A-2002").build()))
        .items().count()
    println("3. retry with a time-based key: both conditional puts succeeded, A-2002 now has $copies payments")
    low.close()
}
