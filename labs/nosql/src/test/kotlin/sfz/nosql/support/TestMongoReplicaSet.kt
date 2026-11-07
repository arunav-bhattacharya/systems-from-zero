package sfz.nosql.support

import com.mongodb.client.MongoClient
import com.mongodb.client.MongoClients
import com.mongodb.client.MongoDatabase
import org.testcontainers.containers.GenericContainer
import org.testcontainers.containers.wait.strategy.Wait
import org.testcontainers.utility.DockerImageName
import java.time.Duration
import java.util.UUID

/**
 * One MongoDB server run as a ONE-member replica set (`rs0`), for the tests that need transactions
 * (lesson 10). [TestMongo] is a standalone server, and a standalone server refuses transactions.
 * Started the first time a test touches it, shared by the whole test JVM, removed when it exits.
 */
object TestMongoReplicaSet {
    /** Pinned: the same image as `labs/env/mongo.yml`. */
    const val IMAGE = "mongo:9.0"
    private const val PORT = 27017

    private val container: GenericContainer<*> by lazy {
        GenericContainer(DockerImageName.parse(IMAGE))
            .withExposedPorts(PORT)
            .withCommand("--replSet", "rs0", "--bind_ip_all", "--wiredTigerCacheSizeGB", "0.25")
            .withCreateContainerCmdModifier { cmd -> cmd.hostConfig?.withMemory(512L * 1024 * 1024) }
            .waitingFor(Wait.forLogMessage(".*Waiting for connections.*", 1).withStartupTimeout(Duration.ofMinutes(2)))
            .also { c ->
                c.start()
                // make it a replica set of one, then wait until it has elected itself primary
                c.execInContainer("mongosh", "--quiet", "--eval", "rs.initiate({_id: 'rs0', members: [{_id: 0, host: 'localhost:27017'}]})")
                val deadline = System.nanoTime() + Duration.ofSeconds(60).toNanos()
                while (c.execInContainer("mongosh", "--quiet", "--eval", "db.hello().isWritablePrimary").stdout.trim() != "true") {
                    check(System.nanoTime() < deadline) { "the replica set never elected a primary" }
                    Thread.sleep(250)
                }
            }
    }

    /** `mongodb://host:port/?directConnection=true`: talk to the one member directly. */
    val connectionString: String get() = "mongodb://${container.host}:${container.getMappedPort(PORT)}/?directConnection=true"

    /** One client for every test. Never close it. */
    val client: MongoClient by lazy { MongoClients.create(connectionString) }

    /** A database no other test uses, such as `l10-3f9c2a1b`. */
    fun freshDatabase(prefix: String): MongoDatabase = client.getDatabase("$prefix-${UUID.randomUUID().toString().take(8)}")
}
