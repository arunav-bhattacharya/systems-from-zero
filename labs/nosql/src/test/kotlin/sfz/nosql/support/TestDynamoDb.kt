package sfz.nosql.support

import org.testcontainers.containers.GenericContainer
import org.testcontainers.utility.DockerImageName
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration
import software.amazon.awssdk.core.interceptor.ExecutionInterceptor
import software.amazon.awssdk.enhanced.dynamodb.DynamoDbEnhancedClient
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import java.net.URI
import java.util.UUID

/**
 * One DynamoDB Local server for the whole test JVM, started the first time a test touches it.
 *
 * Every lesson's tests share this container. Never delete other tests' tables: give each
 * test class (or each test) its own table with [uniqueTableName]. Testcontainers removes
 * the container when the JVM exits.
 *
 * DynamoDB Local runs in memory with `-sharedDb`, so every client sees the same tables
 * whatever access key or Region it sends.
 */
object TestDynamoDb {
    /** Pinned: DynamoDB Local v3, the same image as `labs/env/dynamodb.yml`. */
    const val IMAGE = "amazon/dynamodb-local:3.3.2"
    private const val PORT = 8000

    private val container: GenericContainer<*> by lazy {
        GenericContainer(DockerImageName.parse(IMAGE))
            .withExposedPorts(PORT)
            // the image's entrypoint is `java`; a small heap keeps the shared Docker VM happy
            .withCommand("-Xmx256m", "-jar", "DynamoDBLocal.jar", "-inMemory", "-sharedDb", "-disableTelemetry")
            .withCreateContainerCmdModifier { cmd -> cmd.hostConfig?.withMemory(512L * 1024 * 1024) }
            .also { it.start() }
    }

    /** `http://host:port` of the running server. */
    val endpoint: URI get() = URI.create("http://${container.host}:${container.getMappedPort(PORT)}")

    /**
     * The low-level client, shared by every test. DynamoDB Local accepts any credentials,
     * but the SDK insists on having some, and on a Region. Never close it.
     */
    val client: DynamoDbClient by lazy {
        DynamoDbClient.builder()
            .endpointOverride(endpoint)
            .region(Region.US_EAST_1)
            .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("sfz", "sfz")))
            .build()
    }

    /** The Enhanced Client on top of [client]. Never close it. */
    val enhanced: DynamoDbEnhancedClient by lazy {
        DynamoDbEnhancedClient.builder().dynamoDbClient(client).build()
    }

    /** A table name no other test uses, such as `payments-3f9c2a1b`. */
    fun uniqueTableName(prefix: String): String = "$prefix-${UUID.randomUUID().toString().take(8)}"

    /**
     * A NEW low-level client on the same server, with [interceptors] attached (for example a
     * [RequestLog] that records every request). The caller owns it and should close it.
     */
    fun clientWith(vararg interceptors: ExecutionInterceptor): DynamoDbClient =
        DynamoDbClient.builder()
            .endpointOverride(endpoint)
            .region(Region.US_EAST_1)
            .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("sfz", "sfz")))
            .overrideConfiguration(ClientOverrideConfiguration.builder().apply { interceptors.forEach { addExecutionInterceptor(it) } }.build())
            .build()
}
