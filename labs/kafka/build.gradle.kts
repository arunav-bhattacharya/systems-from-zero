@Suppress("UNCHECKED_CAST")
val versions = rootProject.extra["versions"] as Map<String, String>

dependencies {
    implementation("org.apache.kafka:kafka-clients:${versions["kafka"]}")
    implementation("org.apache.kafka:kafka-streams:${versions["kafka"]}")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:${versions["coroutines"]}")
    runtimeOnly("org.slf4j:slf4j-simple:${versions["slf4j"]}")
    testImplementation("org.apache.kafka:kafka-streams-test-utils:${versions["kafka"]}")
    // the Kafka Streams demos of stream-05 run topologies in TopologyTestDriver, with no broker
    "demoImplementation"("org.apache.kafka:kafka-streams-test-utils:${versions["kafka"]}")
    // stream-02: Avro's own reader/writer schema resolution, for the schema demos and to check the lab's model
    "demoImplementation"("org.apache.avro:avro:1.12.2")
    testImplementation("org.apache.avro:avro:1.12.2")
    // stream-02: the outbox demo writes a payment and its event to PostgreSQL in one transaction
    "demoImplementation"("org.postgresql:postgresql:${versions["postgres"]}")
    testImplementation("org.testcontainers:testcontainers-kafka:${versions["testcontainers"]}")
    testImplementation("org.testcontainers:testcontainers-junit-jupiter:${versions["testcontainers"]}")
}

// The Kafka clients log every config value at INFO when they start. Keep tests and demos quiet:
// warnings and errors only. Pass -Dorg.slf4j.simpleLogger.defaultLogLevel=info to see everything.
val quietLogs = mapOf(
    "org.slf4j.simpleLogger.defaultLogLevel" to "warn",
    "org.slf4j.simpleLogger.log.tc" to "warn",
    // Kafka Streams 4.4 warns at every start that a future 5.0 default will change; the demos don't need it
    "org.slf4j.simpleLogger.log.org.apache.kafka.streams.StreamsConfig" to "error",
    "org.slf4j.simpleLogger.log.org.apache.kafka.streams.TopologyTestDriver" to "error",
)
tasks.withType<Test>().configureEach { systemProperties(quietLogs) }
tasks.named<JavaExec>("demo") { systemProperties(quietLogs) }

// lz4-java loads a native library; JDK 24+ warns about that unless native access is granted
tasks.withType<Test>().configureEach { jvmArgs("--enable-native-access=ALL-UNNAMED") }
tasks.named<JavaExec>("demo") { jvmArgs("--enable-native-access=ALL-UNNAMED") }
