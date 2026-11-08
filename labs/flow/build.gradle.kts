@Suppress("UNCHECKED_CAST")
val versions = rootProject.extra["versions"] as Map<String, String>

// Encoding, APIs and workflows: wire formats without code generation (Protobuf's CodedOutputStream and
// DynamicMessage, Avro's GenericRecord), JSON/CBOR/MessagePack through Jackson, gRPC with hand-written
// method descriptors, and Temporal workflows run in its in-process test server (no Docker).
dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:${versions["coroutines"]}")
    implementation("com.google.protobuf:protobuf-java:4.36.2")
    implementation("com.google.protobuf:protobuf-java-util:4.36.2")
    implementation("org.apache.avro:avro:1.12.2")
    implementation("com.fasterxml.jackson.core:jackson-databind:2.23.0")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin:2.23.0")
    implementation("com.fasterxml.jackson.dataformat:jackson-dataformat-cbor:2.23.0")
    implementation("org.msgpack:jackson-dataformat-msgpack:0.9.12")
    implementation("io.grpc:grpc-netty-shaded:1.85.1")
    implementation("io.grpc:grpc-stub:1.85.1")
    implementation("io.grpc:grpc-protobuf:1.85.1")
    implementation("io.grpc:grpc-inprocess:1.85.1")
    implementation("io.temporal:temporal-sdk:1.40.0")
    implementation("io.temporal:temporal-kotlin:1.40.0")
    implementation("org.postgresql:postgresql:${versions["postgres"]}")
    runtimeOnly("org.slf4j:slf4j-simple:${versions["slf4j"]}")
    testImplementation("io.temporal:temporal-testing:1.40.0")
    "demoImplementation"("io.temporal:temporal-testing:1.40.0")
    testImplementation("org.testcontainers:testcontainers-postgresql:${versions["testcontainers"]}")
    testImplementation("org.testcontainers:testcontainers-junit-jupiter:${versions["testcontainers"]}")
}

val quietLogs = mapOf("org.slf4j.simpleLogger.defaultLogLevel" to "warn")
tasks.withType<Test>().configureEach { systemProperties(quietLogs) }
tasks.named<JavaExec>("demo") { systemProperties(quietLogs) }

// msgpack-core uses sun.misc.Unsafe, which JDK 24+ warns about on first use; the labs allow it quietly.
// The flag exists from JDK 23, so add it only when the JVM running the task knows it.
val unsafeOk = listOf("--sun-misc-unsafe-memory-access=allow")
tasks.withType<Test>().configureEach {
    jvmArgumentProviders.add(CommandLineArgumentProvider {
        if ((javaLauncher.orNull?.metadata?.languageVersion?.asInt() ?: JavaVersion.current().majorVersion.toInt()) >= 23) unsafeOk else emptyList()
    })
}
tasks.named<JavaExec>("demo") {
    jvmArgumentProviders.add(CommandLineArgumentProvider {
        if ((javaLauncher.orNull?.metadata?.languageVersion?.asInt() ?: JavaVersion.current().majorVersion.toInt()) >= 23) unsafeOk else emptyList()
    })
}
