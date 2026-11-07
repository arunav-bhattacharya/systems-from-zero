package sfz.redis.support

import org.testcontainers.containers.GenericContainer
import org.testcontainers.utility.DockerImageName
import redis.clients.jedis.RedisClient

/**
 * One Redis server for the whole test JVM, started the first time a test touches it.
 *
 * Every lesson's tests share this container. Never FLUSHALL it: give each test its own
 * keys with [KeySpace] instead. Testcontainers removes the container when the JVM exits.
 *
 * The server runs the image's default configuration, so the defaults the lessons teach
 * (encoding thresholds, `io-threads 1`, `noeviction`) hold here. A test that needs other
 * settings should change them with CONFIG SET and put them back in a `finally`.
 */
object TestRedis {
    /** Pinned, so encoding thresholds and the command set never drift under the tests. */
    const val IMAGE = "redis:8.10.3"
    private const val PORT = 6379

    private val container: GenericContainer<*> by lazy {
        GenericContainer(DockerImageName.parse(IMAGE))
            .withExposedPorts(PORT)
            // several writers share one Docker VM: keep the test server small
            .withCreateContainerCmdModifier { cmd -> cmd.hostConfig?.withMemory(256L * 1024 * 1024) }
            .also { it.start() }
    }

    val host: String get() = container.host
    val port: Int get() = container.getMappedPort(PORT)

    /** `redis://host:port`, the form Lettuce takes. */
    val uri: String get() = "redis://$host:$port"

    /**
     * A Jedis client shared by every test, for setup and assertions. It pools its
     * connections, so it is safe to use from several threads. Never close it.
     */
    val jedis: RedisClient by lazy { newJedis() }

    /**
     * A new Jedis client with its own connection pool. Use it when a test needs a client
     * that is really separate from [jedis] (a second "application"). Close it when done.
     */
    fun newJedis(): RedisClient = RedisClient.builder().hostAndPort(host, port).build()

    /**
     * A Lettuce client (the entry point, not a connection) shared by every test.
     * Open connections with `lettuce.connect()` and close them; never shut this down.
     */
    val lettuce: io.lettuce.core.RedisClient by lazy { io.lettuce.core.RedisClient.create(uri) }
}
