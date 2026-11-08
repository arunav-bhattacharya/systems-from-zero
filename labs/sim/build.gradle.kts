@Suppress("UNCHECKED_CAST")
val versions = rootProject.extra["versions"] as Map<String, String>

// Simulations: queues and percentiles, networks that drop and delay, clocks that drift, pausing processes,
// logical clocks, consensus and dataflow pipelines, all as plain Kotlin on a seeded, deterministic scheduler.
// No Docker. Property-based tests use jqwik.
dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:${versions["coroutines"]}")
    testImplementation("net.jqwik:jqwik:1.10.2")
}
