package sfz.nosql.l16.demo

import software.amazon.awssdk.auth.credentials.AwsBasicCredentials
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider
import software.amazon.awssdk.awscore.retry.AwsRetryStrategy
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.AttributeDefinition
import software.amazon.awssdk.services.dynamodb.model.AttributeValue
import software.amazon.awssdk.services.dynamodb.model.BillingMode
import software.amazon.awssdk.services.dynamodb.model.KeySchemaElement
import software.amazon.awssdk.services.dynamodb.model.KeyType
import software.amazon.awssdk.services.dynamodb.model.ProvisionedThroughputExceededException
import software.amazon.awssdk.services.dynamodb.model.ReturnConsumedCapacity
import software.amazon.awssdk.services.dynamodb.model.ScalarAttributeType
import java.net.URI
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.DoubleAdder

/**
 * A table provisioned with ONE write unit a second, then 1,000 writes from eight threads, as fast as
 * they can send them. Real DynamoDB would admit about one a second plus a few hundred saved-up burst units, and
 * throttle the rest. DynamoDB Local is one process with no partitions and no admission control.
 */
fun main() {
    val ddb = DynamoDbClient.builder()
        .endpointOverride(URI.create("http://localhost:8000"))
        .region(Region.US_EAST_1)
        .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("sfz", "sfz")))
        // no SDK retries: a throttle would reach this code instead of being retried quietly
        .overrideConfiguration { it.retryStrategy(AwsRetryStrategy.doNotRetry()) }
        .build()
    val table = "one-wcu"
    if (table in ddb.listTables().tableNames()) ddb.deleteTable { it.tableName(table) }

    // provisioned mode: 1 read unit and 1 write unit a second for the whole table
    ddb.createTable {
        it.tableName(table)
            .attributeDefinitions(AttributeDefinition.builder().attributeName("pk").attributeType(ScalarAttributeType.S).build())
            .keySchema(KeySchemaElement.builder().attributeName("pk").keyType(KeyType.HASH).build())
            .billingMode(BillingMode.PROVISIONED)
            .provisionedThroughput { p -> p.readCapacityUnits(1).writeCapacityUnits(1) }
    }
    val provisioned = ddb.describeTable { it.tableName(table) }.table().provisionedThroughput()
    println("provisioned: ${provisioned.readCapacityUnits()} RCU, ${provisioned.writeCapacityUnits()} WCU")

    val consumed = DoubleAdder()
    val throttled = AtomicInteger()
    val started = System.nanoTime()
    val pool = Executors.newFixedThreadPool(8)
    for (i in 0 until 1_000) pool.execute {
        try {
            val r = ddb.putItem {
                it.tableName(table)
                    .item(mapOf(
                        "pk" to AttributeValue.fromS("PAY#pay-%06d".format(i)),
                        "amountMinor" to AttributeValue.fromN((500 + i * 7919 % 9501).toString()),
                    ))
                    .returnConsumedCapacity(ReturnConsumedCapacity.TOTAL)
            }
            consumed.add(r.consumedCapacity().capacityUnits())
        } catch (e: ProvisionedThroughputExceededException) {
            throttled.incrementAndGet() // what real DynamoDB sends when a table or a partition is out of tokens
        }
    }
    pool.shutdown()
    pool.awaitTermination(1, TimeUnit.MINUTES)
    val seconds = (System.nanoTime() - started) / 1e9
    println("wrote 1,000 items in %.1f s, about %,d a second".format(seconds, (1_000 / seconds).toLong()))
    println("write units consumed: %,.1f".format(consumed.sum()))
    println("throttled: $throttled")

    ddb.deleteTable { it.tableName(table) }
    ddb.close()
}
