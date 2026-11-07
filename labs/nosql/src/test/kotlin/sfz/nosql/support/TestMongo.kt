package sfz.nosql.support

import com.mongodb.client.MongoClient
import com.mongodb.client.MongoClients
import com.mongodb.client.MongoDatabase
import org.bson.Document
import org.testcontainers.mongodb.MongoDBContainer
import org.testcontainers.utility.DockerImageName
import java.util.UUID

/**
 * One MongoDB server for the whole test JVM, started the first time a test touches it.
 *
 * Every lesson's tests share this container. Give each test class (or each test) its own
 * database with [freshDatabase], so tests never see each other's documents. Testcontainers
 * removes the container when the JVM exits.
 *
 * It's a standalone server, not a replica set: the lab tests documents, indexes and pipelines,
 * and the replica set Try-it in lesson 8 uses `labs/env/mongo-rs.yml` instead.
 */
object TestMongo {
    /** Pinned: the same image as `labs/env/mongo.yml`. */
    const val IMAGE = "mongo:9.0"

    private val container: MongoDBContainer by lazy {
        MongoDBContainer(DockerImageName.parse(IMAGE))
            // a small WiredTiger cache and a memory limit keep the shared Docker VM happy
            .withCommand("--wiredTigerCacheSizeGB", "0.25")
            .withCreateContainerCmdModifier { cmd -> cmd.hostConfig?.withMemory(768L * 1024 * 1024) }
            .also { it.start() }
    }

    /** `mongodb://host:port/?directConnection=true` of the running server. */
    val connectionString: String get() = container.connectionString + "/?directConnection=true"

    /** One client for every test. Never close it. */
    val client: MongoClient by lazy { MongoClients.create(connectionString) }

    /** A database no other test uses, such as `payments-3f9c2a1b`. */
    fun freshDatabase(prefix: String): MongoDatabase = client.getDatabase("$prefix-${UUID.randomUUID().toString().take(8)}")

    /**
     * Every `stage` name in an explain document, depth first, so a test can say "this plan has an
     * IXSCAN and no SORT" whatever engine (classic or slot-based) produced it.
     */
    fun stages(explain: Any?): List<String> = when (explain) {
        is Document -> explain.entries.flatMap { (k, v) -> (if (k == "stage" && v is String) listOf(v) else emptyList()) + stages(v) }
        is List<*> -> explain.flatMap { stages(it) }
        else -> emptyList()
    }

    /** Every sub-document of an explain that has [key], depth first (for example every IXSCAN stage's `indexName`). */
    fun find(explain: Any?, key: String): List<Document> = when (explain) {
        is Document -> (if (explain.containsKey(key)) listOf(explain) else emptyList()) + explain.values.flatMap { find(it, key) }
        is List<*> -> explain.flatMap { find(it, key) }
        else -> emptyList()
    }
}
