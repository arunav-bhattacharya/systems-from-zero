package sfz.redis.support

import org.apache.commons.pool2.impl.GenericObjectPoolConfig
import org.testcontainers.containers.GenericContainer
import org.testcontainers.utility.DockerImageName
import redis.clients.jedis.Connection
import redis.clients.jedis.RedisClient
import redis.clients.jedis.exceptions.JedisException

/**
 * A Redis server that the persistence tests (lesson 9) can crash on purpose, started the first time
 * a test touches it and shared by every test in the JVM.
 *
 * Inside the container a small shell loop runs `redis-server /conf/redis.conf` and starts it again
 * whenever it dies, so [crash] is a real `kill -9` of the server process: no shutdown, no final save,
 * no last fsync. The container, its files and its mapped port stay, so the restarted server loads
 * whatever reached `/data` before the kill, exactly as a server restarted by systemd or Kubernetes would.
 *
 * Like [EvictionRedis], this server belongs to its tests alone: [restartWith] wipes it. Never point
 * other tests at it, and never FLUSHALL [TestRedis].
 */
object CrashRedis {
    private const val PORT = 6379

    /**
     * No append-only file and no automatic save points: the data lives in memory only, and the one
     * snapshot on disk is the one a test makes itself with BGSAVE.
     */
    val NO_PERSISTENCE = listOf("save \"\"", "appendonly no")

    /** The append-only file with the given fsync policy (`always`, `everysec` or `no`), and no RDB save points. */
    fun aof(fsync: String) = listOf("save \"\"", "appendonly yes", "appendfsync $fsync")

    // the loop: start the server unless /tmp/hold exists, remember its pid, wait for it to die, repeat
    private const val LOOP = "mkdir -p /conf && touch /conf/redis.conf && " +
        "while true; do " +
        "if [ -f /tmp/hold ]; then sleep 0.05; continue; fi; " +
        "redis-server /conf/redis.conf & echo \$! > /tmp/redis.pid; wait \$!; " +
        "done"

    private val container: GenericContainer<*> by lazy {
        GenericContainer(DockerImageName.parse(TestRedis.IMAGE))
            .withExposedPorts(PORT)
            .withCommand("sh", "-c", LOOP)
            .withCreateContainerCmdModifier { cmd -> cmd.hostConfig?.withMemory(64L * 1024 * 1024) }
            .also { it.start() }
    }

    val host: String get() = container.host
    val port: Int get() = container.getMappedPort(PORT)

    /**
     * A Jedis client for this server, shared by the persistence tests. Its pool checks each connection
     * with PING before lending it, so connections broken by a crash are replaced instead of failing the
     * next command. Never close it.
     */
    val jedis: RedisClient by lazy {
        val pool = GenericObjectPoolConfig<Connection>().apply { testOnBorrow = true }
        RedisClient.builder().hostAndPort(host, port).poolConfig(pool).build()
    }

    /**
     * Stops the server, deletes everything in `/data`, writes a fresh config file with [settings]
     * (one `redis.conf` line each), and starts the server again. Returns once it answers PING.
     */
    fun restartWith(settings: List<String>) {
        val conf = (listOf("port $PORT", "protected-mode no", "dir /data") + settings).joinToString("\n")
        exec("touch /tmp/hold; kill -9 \$(cat /tmp/redis.pid) 2>/dev/null; sleep 0.2; " +
            "rm -rf /data/* /data/.[!.]*; printf '%s\\n' '${conf.replace("'", "'\\''")}' > /conf/redis.conf; rm -f /tmp/hold")
        awaitReady()
    }

    /** Kills the server process with SIGKILL, lets the loop start it again, and waits until it has loaded its files. */
    fun crash() {
        exec("kill -9 \$(cat /tmp/redis.pid)")
        awaitReady()
    }

    private fun exec(script: String) {
        val result = container.execInContainer("sh", "-c", script)
        check(result.exitCode == 0) { "shell step failed (${result.exitCode}): ${result.stderr}" }
    }

    /** Polls with fresh connections until the new process answers PING (it answers LOADING while it reads its files). */
    private fun awaitReady() {
        Thread.sleep(100)                                    // let the old process die before we ask
        val deadline = System.nanoTime() + 20_000_000_000L
        while (System.nanoTime() < deadline) {
            try {
                RedisClient.builder().hostAndPort(host, port).build().use { probe ->
                    if (probe.ping() == "PONG") return
                }
            } catch (e: JedisException) {
                // not listening yet, or still loading: try again
            }
            Thread.sleep(50)
        }
        error("the crash test Redis did not come back within 20 s")
    }
}
