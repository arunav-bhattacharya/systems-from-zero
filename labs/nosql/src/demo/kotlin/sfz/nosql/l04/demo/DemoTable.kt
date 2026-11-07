package sfz.nosql.l04.demo

import software.amazon.awssdk.auth.credentials.AwsBasicCredentials
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.AttributeDefinition
import software.amazon.awssdk.services.dynamodb.model.AttributeValue
import software.amazon.awssdk.services.dynamodb.model.BillingMode
import software.amazon.awssdk.services.dynamodb.model.GlobalSecondaryIndex
import software.amazon.awssdk.services.dynamodb.model.KeySchemaElement
import software.amazon.awssdk.services.dynamodb.model.KeyType
import software.amazon.awssdk.services.dynamodb.model.Projection
import software.amazon.awssdk.services.dynamodb.model.ProjectionType
import software.amazon.awssdk.services.dynamodb.model.ScalarAttributeType
import java.net.URI

// Shared by the lesson 4 demos: the single payments table and a few items to read.

/** DynamoDB Local from env/dynamodb.yml; any credentials and Region work. */
fun localClient(): DynamoDbClient = DynamoDbClient.builder()
    .endpointOverride(URI.create("http://localhost:8000"))
    .region(Region.US_EAST_1)
    .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("sfz", "sfz")))
    .build()

fun s(v: String): AttributeValue = AttributeValue.fromS(v)
fun n(v: Long): AttributeValue = AttributeValue.fromN(v.toString())

/** The table: pk/sk, plus byPayment (paymentId; sk) and byMerchant (merchantId; status, createdAt). Recreated on every run. */
fun createPaymentsTable(ddb: DynamoDbClient, table: String) {
    fun attr(name: String) = AttributeDefinition.builder().attributeName(name).attributeType(ScalarAttributeType.S).build()
    fun hash(name: String) = KeySchemaElement.builder().attributeName(name).keyType(KeyType.HASH).build()
    fun range(name: String) = KeySchemaElement.builder().attributeName(name).keyType(KeyType.RANGE).build()
    val all = Projection.builder().projectionType(ProjectionType.ALL).build()
    runCatching { ddb.deleteTable { it.tableName(table) } }
    ddb.createTable {
        it.tableName(table).billingMode(BillingMode.PAY_PER_REQUEST)
            .attributeDefinitions(attr("pk"), attr("sk"), attr("paymentId"), attr("merchantId"), attr("status"), attr("createdAt"))
            .keySchema(hash("pk"), range("sk"))
            .globalSecondaryIndexes(
                GlobalSecondaryIndex.builder().indexName("byPayment").keySchema(hash("paymentId"), range("sk")).projection(all).build(),
                GlobalSecondaryIndex.builder().indexName("byMerchant")
                    .keySchema(hash("merchantId"), range("status"), range("createdAt")).projection(all).build(),
            )
    }
}

/** Two accounts with payments, ledger entries and refunds, written in no particular order. */
fun seedPayments(ddb: DynamoDbClient, table: String) {
    fun put(item: Map<String, AttributeValue>) = ddb.putItem { it.tableName(table).item(item) }
    fun profile(account: String, customer: String, balance: Long) = put(mapOf(
        "pk" to s("ACCT#$account"), "sk" to s("PROFILE"), "type" to s("ACCOUNT"),
        "accountId" to s(account), "customerId" to s(customer), "currency" to s("EUR"), "balanceMinor" to n(balance),
    ))
    fun payment(account: String, id: String, at: String, merchant: String, status: String, amount: Long) = put(mapOf(
        "pk" to s("ACCT#$account"), "sk" to s("PAY#$at#$id"), "type" to s("PAYMENT"),
        "paymentId" to s(id), "accountId" to s(account), "merchantId" to s(merchant), "status" to s(status),
        "amountMinor" to n(amount), "currency" to s("EUR"), "createdAt" to s(at),
    ))
    fun refund(account: String, id: String, paymentId: String, at: String, amount: Long) = put(mapOf(
        "pk" to s("ACCT#$account"), "sk" to s("REFUND#$at#$id"), "type" to s("REFUND"),
        "refundId" to s(id), "paymentId" to s(paymentId), "accountId" to s(account), "amountMinor" to n(amount), "createdAt" to s(at),
    ))
    fun ledger(account: String, transferId: String, at: String, amount: Long) = put(mapOf(
        "pk" to s("ACCT#$account"), "sk" to s("LEDGER#$at#$transferId"), "type" to s("LEDGER"),
        "transferId" to s(transferId), "amountMinor" to n(amount),
    ))
    payment("A-1001", "pay-81723", "2026-11-07T10:15:03.120Z", "M-0042", "SETTLED", 4250)
    ledger("A-1001", "txf-300", "2026-11-06T17:00:00.000Z", -2000)
    refund("A-1001", "ref-12", "pay-81723", "2026-11-07T11:02:00.000Z", 1000)
    payment("A-1001", "pay-80911", "2026-11-06T18:40:51.004Z", "M-0042", "SETTLED", 1999)
    profile("A-1001", "C-77", 10_000)
    payment("A-1001", "pay-81720", "2026-11-07T09:40:27.000Z", "M-0042", "FAILED", 7300)
    ledger("A-1001", "txf-301", "2026-11-07T09:00:00.000Z", 5000)
    payment("A-1001", "pay-81701", "2026-11-07T08:15:03.000Z", "M-0042", "SETTLED", 18000)
    refund("A-1001", "ref-14", "pay-81723", "2026-11-07T12:10:00.000Z", 300)
    payment("A-1001", "pay-81730", "2026-11-07T10:30:12.000Z", "M-0043", "SETTLED", 4250)
    profile("A-2002", "C-91", 5_000)
    payment("A-2002", "pay-81724", "2026-11-07T09:55:00.000Z", "M-0042", "FAILED", 1200)
    payment("A-2002", "pay-81741", "2026-11-07T11:20:45.000Z", "M-0042", "FAILED", 990)
}
