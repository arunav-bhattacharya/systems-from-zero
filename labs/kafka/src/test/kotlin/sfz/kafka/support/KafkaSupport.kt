package sfz.kafka.support

import org.apache.kafka.clients.admin.Admin
import org.apache.kafka.clients.admin.AdminClientConfig
import org.apache.kafka.clients.admin.AlterConfigOp
import org.apache.kafka.clients.admin.ConfigEntry
import org.apache.kafka.clients.admin.NewTopic
import org.apache.kafka.clients.admin.OffsetSpec
import org.apache.kafka.clients.consumer.ConsumerConfig
import org.apache.kafka.clients.consumer.KafkaConsumer
import org.apache.kafka.clients.consumer.KafkaShareConsumer
import org.apache.kafka.clients.producer.KafkaProducer
import org.apache.kafka.clients.producer.ProducerConfig
import org.apache.kafka.common.TopicPartition
import org.apache.kafka.common.config.ConfigResource
import org.apache.kafka.common.serialization.StringDeserializer
import org.apache.kafka.common.serialization.StringSerializer
import org.testcontainers.kafka.KafkaContainer
import org.testcontainers.utility.DockerImageName
import java.util.UUID
import java.util.concurrent.TimeUnit

/**
 * One single-node Kafka broker for the whole test JVM, started the first time a test asks for it.
 * Testcontainers' Ryuk sidecar removes the container when the JVM exits.
 *
 * How a test class uses it (Kotlin or Java):
 *
 * - call [start] from a `@BeforeAll` method, so the container start counts against the
 *   3-minute `@BeforeAll` timeout and not the 60-second test timeout;
 * - make its own topics with [newTopic]: every name gets a random suffix, so tests never read each other's records;
 * - get clients from [producer] and [consumer] (String keys and values) and close them with `use` / try-with-resources.
 */
object KafkaSupport {
    /** The broker image. The GraalVM native build starts in about a second and needs far less memory than the JVM one. */
    const val IMAGE = "apache/kafka-native:4.4.0"

    private val container: KafkaContainer by lazy {
        KafkaContainer(DockerImageName.parse(IMAGE))
            // Lab speed-ups, broker-wide. Topic defaults (7-day retention, 1 GiB segments) are unchanged.
            // Check retention every second (default 5 minutes), starting right away (default: 30 s after start-up).
            .withEnv("KAFKA_LOG_RETENTION_CHECK_INTERVAL_MS", "1000")
            .withEnv("KAFKA_LOG_INITIAL_TASK_DELAY_MS", "0")
            // Let the log cleaner (compaction) look for work every second (default 15 s).
            .withEnv("KAFKA_LOG_CLEANER_BACKOFF_MS", "1000")
            .withEnv("KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS", "0")
            // Groups on the new protocol (group.protocol=consumer) hear about new assignments on their heartbeat:
            // every second here instead of every 5 s, so a rebalance test takes seconds, not tens of seconds.
            .withEnv("KAFKA_GROUP_CONSUMER_MIN_HEARTBEAT_INTERVAL_MS", "500")
            .withEnv("KAFKA_GROUP_CONSUMER_HEARTBEAT_INTERVAL_MS", "1000")
            // One broker, so the transaction state topic gets one replica (the defaults, 3 and 2, need three brokers).
            .withEnv("KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR", "1")
            .withEnv("KAFKA_TRANSACTION_STATE_LOG_MIN_ISR", "1")
            // Share groups (lesson 12): the same for the share-group state topic, __share_group_state.
            .withEnv("KAFKA_SHARE_COORDINATOR_STATE_TOPIC_REPLICATION_FACTOR", "1")
            .withEnv("KAFKA_SHARE_COORDINATOR_STATE_TOPIC_MIN_ISR", "1")
            // Share consumers hear about their assignment on the heartbeat too: every second instead of every 5 s.
            .withEnv("KAFKA_GROUP_SHARE_MIN_HEARTBEAT_INTERVAL_MS", "500")
            .withEnv("KAFKA_GROUP_SHARE_HEARTBEAT_INTERVAL_MS", "1000")
            .also { it.start() }
    }

    /** One admin client shared by the helpers below; closed when the JVM exits. */
    private val sharedAdmin: Admin by lazy {
        admin().also { a -> Runtime.getRuntime().addShutdownHook(Thread { a.close() }) }
    }

    /** Starts the broker if it is not running yet. Call it from `@BeforeAll`. */
    @JvmStatic
    fun start() {
        container
    }

    /** host:port of the broker, for `bootstrap.servers`. */
    @JvmStatic
    val bootstrapServers: String
        get() = container.bootstrapServers

    /** A new admin client. Close it when you are done. */
    @JvmStatic
    fun admin(): Admin = Admin.create(mapOf<String, Any>(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG to bootstrapServers))

    /**
     * Creates a topic named `<prefix>-<8 random hex chars>` with one replica and returns its name.
     * [configs] are topic configs, for example `mapOf("segment.bytes" to "1048576")`.
     */
    @JvmStatic
    @JvmOverloads
    fun newTopic(prefix: String, partitions: Int = 1, configs: Map<String, String> = emptyMap()): String {
        val name = "$prefix-${UUID.randomUUID().toString().take(8)}"
        val topic = NewTopic(name, partitions, 1.toShort()).configs(configs)
        sharedAdmin.createTopics(listOf(topic)).all().get(30, TimeUnit.SECONDS)
        awaitLeaders(name, partitions)
        return name
    }

    /**
     * Waits until partitions 0 until [partitions] of [topic] each answer on their leader. Right after a topic is
     * created (or grown), the broker can list a partition in its metadata a few milliseconds before it is ready
     * to lead it, and a first produce then gets NOT_LEADER_OR_FOLLOWER. A ListOffsets request goes to the leader
     * too, so once every partition answers one, produce requests will find their leaders. It writes nothing.
     */
    @JvmStatic
    fun awaitLeaders(topic: String, partitions: Int) {
        val tps = (0 until partitions).map { TopicPartition(topic, it) }
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(30)
        while (true) {
            try {
                sharedAdmin.listOffsets(tps.associateWith { OffsetSpec.latest() }).all().get(10, TimeUnit.SECONDS)
                return
            } catch (e: Exception) {
                if (System.nanoTime() > deadline) throw IllegalStateException("partitions of $topic have no leader yet", e)
                Thread.sleep(100)
            }
        }
    }

    /** A String/String producer with the client defaults (acks=all, idempotence on). [extra] overrides any setting. */
    @JvmStatic
    @JvmOverloads
    fun producer(extra: Map<String, Any> = emptyMap()): KafkaProducer<String, String> =
        KafkaProducer(
            mapOf<String, Any>(
                ProducerConfig.BOOTSTRAP_SERVERS_CONFIG to bootstrapServers,
                ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG to StringSerializer::class.java,
                ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG to StringSerializer::class.java,
            ) + extra,
        )

    /**
     * A String/String consumer that belongs to no group: use `assign` and `seek`, not `subscribe`.
     * Auto commit is off and `auto.offset.reset` is `earliest`. Pass `group.id` in [extra] to join a group.
     */
    @JvmStatic
    @JvmOverloads
    fun consumer(extra: Map<String, Any> = emptyMap()): KafkaConsumer<String, String> =
        KafkaConsumer(
            mapOf<String, Any>(
                ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG to bootstrapServers,
                ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG to StringDeserializer::class.java,
                ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG to StringDeserializer::class.java,
                ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG to false,
                ConsumerConfig.AUTO_OFFSET_RESET_CONFIG to "earliest",
            ) + extra,
        )

    /**
     * A String/String share consumer in share group [group] (lesson 12). Call `subscribe`, then `poll`.
     * [extra] adds or overrides settings, for example `share.acknowledgement.mode` = `explicit`.
     */
    @JvmStatic
    @JvmOverloads
    fun shareConsumer(group: String, extra: Map<String, Any> = emptyMap()): KafkaShareConsumer<String, String> =
        KafkaShareConsumer(
            mapOf<String, Any>(
                ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG to bootstrapServers,
                ConsumerConfig.GROUP_ID_CONFIG to group,
                ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG to StringDeserializer::class.java,
                ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG to StringDeserializer::class.java,
            ) + extra,
        )

    /**
     * Sets dynamic group configs on [group], which need not exist yet, for example
     * `mapOf("share.auto.offset.reset" to "earliest")`. Share groups read most of their settings this way.
     */
    @JvmStatic
    fun setGroupConfig(group: String, configs: Map<String, String>) {
        val ops = configs.map { (k, v) -> AlterConfigOp(ConfigEntry(k, v), AlterConfigOp.OpType.SET) }
        sharedAdmin.incrementalAlterConfigs(mapOf(ConfigResource(ConfigResource.Type.GROUP, group) to ops)).all().get(30, TimeUnit.SECONDS)
    }
}
