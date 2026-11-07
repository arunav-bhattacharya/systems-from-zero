@Suppress("UNCHECKED_CAST")
val versions = rootProject.extra["versions"] as Map<String, String>

dependencies {
    implementation("redis.clients:jedis:${versions["jedis"]}")
    implementation("io.lettuce:lettuce-core:${versions["lettuce"]}")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:${versions["coroutines"]}")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-reactive:${versions["coroutines"]}")
    runtimeOnly("org.slf4j:slf4j-simple:${versions["slf4j"]}")
    // lesson 8's watchdog demo only: what a production lock library does. Pinned here because the
    // root versions map has no Redisson entry; the exercises and tests never use it.
    "demoImplementation"("org.redisson:redisson:4.8.0")
    testImplementation("org.testcontainers:testcontainers:${versions["testcontainers"]}")
    testImplementation("org.testcontainers:testcontainers-junit-jupiter:${versions["testcontainers"]}")
}

// Testcontainers and Netty log at INFO by default, which buries the test results and demo output.
// The Netty line silenced here is a harmless macOS DNS-resolver notice that Lettuce triggers.
val quietLogs = mapOf(
    "org.slf4j.simpleLogger.defaultLogLevel" to "warn",
    "org.slf4j.simpleLogger.log.io.netty.resolver.dns.DnsServerAddressStreamProviders" to "error",
)
tasks.withType<Test>().configureEach { systemProperties(quietLogs) }
tasks.named<JavaExec>("demo") { systemProperties(quietLogs) }
