package sfz.redis.support

import org.testcontainers.containers.GenericContainer
import org.testcontainers.utility.DockerImageName
import redis.clients.jedis.RedisClient

/**
 * A second, deliberately tiny Redis server for the eviction tests (lesson 5 of the cache track), started the first
 * time a test touches it and shared by every test in the JVM.
 *
 * It runs with `maxmemory 4mb`. An empty Redis 8.10 already uses about 1.4 MB, so about 2,000
 * values of 1 KB fit. Eviction looks at the whole server, not at one key prefix, so this server
 * belongs to the eviction tests alone: [reset] empties it with FLUSHALL before each test. Never
 * point other tests at it, and never FLUSHALL [TestRedis].
 */
object EvictionRedis {
    const val MAXMEMORY_BYTES = 4L * 1024 * 1024
    private const val PORT = 6379

    private val container: GenericContainer<*> by lazy {
        GenericContainer(DockerImageName.parse(TestRedis.IMAGE))
            .withExposedPorts(PORT)
            // no snapshots: this server is filled up and thrown away
            .withCommand("redis-server", "--maxmemory", MAXMEMORY_BYTES.toString(), "--maxmemory-policy", "noeviction", "--save", "")
            .withCreateContainerCmdModifier { cmd -> cmd.hostConfig?.withMemory(64L * 1024 * 1024) }
            .also { it.start() }
    }

    val host: String get() = container.host
    val port: Int get() = container.getMappedPort(PORT)

    /** A Jedis client for this server, shared by the eviction tests. Never close it. */
    val jedis: RedisClient by lazy { RedisClient.builder().hostAndPort(host, port).build() }

    /**
     * Empties the server and sets the eviction [policy] (for example `allkeys-lru`), so every test
     * starts from the same state. INFO counters such as `evicted_keys` keep counting across tests:
     * read them before and after, and compare.
     */
    fun reset(policy: String) {
        jedis.flushAll()
        jedis.configSet("maxmemory-policy", policy)
    }
}
