package sfz.batch.l09.demo

import org.apache.spark.scheduler.SparkListener
import org.apache.spark.scheduler.SparkListenerJobStart
import org.apache.spark.scheduler.SparkListenerTaskEnd
import java.io.File
import java.util.concurrent.atomic.AtomicInteger

/**
 * Starts a Spark Connect server inside this JVM (a classic local Spark driver with the Connect
 * plugin), then runs SettlementClient as a second JVM that has only the thin client on its
 * classpath. Everything stays on 127.0.0.1.
 */
fun main() {
    val port = 15002                                               // Spark Connect's default port
    val spark = demoSpark {
        config("spark.plugins", "org.apache.spark.sql.connect.SparkConnectPlugin")
        config("spark.connect.grpc.binding.address", "127.0.0.1")
        config("spark.connect.grpc.binding.port", port.toString())
    }
    val payments = File("build/l08/payments").absolutePath
    demoPayments(spark)
    val jobs = AtomicInteger()
    val tasks = AtomicInteger()
    spark.sparkContext().addSparkListener(object : SparkListener() {
        override fun onJobStart(jobStart: SparkListenerJobStart) { jobs.incrementAndGet() }
        override fun onTaskEnd(taskEnd: SparkListenerTaskEnd) { tasks.incrementAndGet() }
    })
    val serverJars = System.getProperty("java.class.path").split(File.pathSeparator).size
    println("server: Spark ${spark.version()} driver with a Connect endpoint at sc://127.0.0.1:$port ($serverJars jars and folders on its classpath)")

    val clientClasspath = System.getProperty("sfz.connect.client.classpath") ?: error("run me with ./gradlew :bigdata:demo")
    val classesDir = clientClasspath.split(File.pathSeparator).first { it.endsWith("classes/java/connectClient") }
    val java = File(System.getProperty("java.home"), "bin/java").path
    val client = ProcessBuilder(
        java, "-cp", clientClasspath, "--add-opens=java.base/java.nio=ALL-UNNAMED",
        "sfz.batch.l09.client.SettlementClient", "sc://127.0.0.1:$port", payments, classesDir,
    ).inheritIO().start()
    val exit = client.waitFor()
    spark.sparkContext().listenerBus().waitUntilEmpty()
    println("server: the client exited with $exit; its queries ran here, in this JVM, as ${jobs.get()} jobs and ${tasks.get()} tasks")
    spark.stop()
}
