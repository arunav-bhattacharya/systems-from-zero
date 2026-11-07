@Suppress("UNCHECKED_CAST")
val versions = rootProject.extra["versions"] as Map<String, String>

// Spark 4.1 is the newest line that both Iceberg 1.12 and Delta 4.4 support, and it runs on Java 17 or 21.
// This module compiles and runs on a JDK 21 toolchain (Gradle downloads one if you don't have it).
kotlin { jvmToolchain(21) }

// Lesson 8: a Spark Connect client is a separate program with its own small classpath. It lives in
// its own source set so its jar never meets the full Spark jars (the two carry clashing copies of
// some classes). The demo JVM runs the Connect server and starts the client as a second JVM.
val connectClient: SourceSet = sourceSets.create("connectClient")

dependencies {
    implementation("org.apache.spark:spark-sql_2.13:4.1.4")
    implementation("org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.12.0")
    implementation("org.duckdb:duckdb_jdbc:2.0.0.1")
    // lesson 10: SQLite as the database behind an Iceberg JDBC catalog, for the catalog demo only
    "demoImplementation"("org.xerial:sqlite-jdbc:3.54.1.0")
    // the Spark Connect server (a plugin of the driver), for the lesson 8 demo only
    "demoImplementation"("org.apache.spark:spark-connect_2.13:4.1.4")
    // the thin JVM client: one shaded jar plus the Scala library
    "connectClientImplementation"("org.apache.spark:spark-connect-client-jvm_2.13:4.1.4")
}

// the module flags spark-submit adds for you; an embedded SparkSession needs them too
val sparkJvmArgs = listOf(
    "java.lang", "java.lang.invoke", "java.lang.reflect", "java.io", "java.net", "java.nio", "java.util",
    "java.util.concurrent", "java.util.concurrent.atomic", "sun.nio.ch", "sun.nio.cs", "sun.security.action", "sun.util.calendar",
).map { "--add-opens=java.base/$it=ALL-UNNAMED" } + listOf("-Djdk.reflect.useDirectMethodHandle=false", "-Xmx2g")

tasks.withType<Test>().configureEach { jvmArgs(sparkJvmArgs) }
tasks.withType<JavaExec>().configureEach { jvmArgs(sparkJvmArgs) }

// the demo tells the lesson 8 server demo where the client's classes and jars are
tasks.named<JavaExec>("demo") {
    dependsOn(connectClient.classesTaskName)
    val clientClasspath = connectClient.runtimeClasspath
    jvmArgumentProviders.add(CommandLineArgumentProvider { listOf("-Dsfz.connect.client.classpath=${clientClasspath.asPath}") })
}
