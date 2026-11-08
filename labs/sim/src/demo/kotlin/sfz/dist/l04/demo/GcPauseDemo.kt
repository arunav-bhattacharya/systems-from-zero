package sfz.dist.l04.demo

import java.nio.file.Files
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.random.Random

/**
 * Lesson dist-04, section 2: how long a JVM stops your threads, by collector. The demo starts three child JVMs with a
 * 1 GB heap: Serial (one thread, stops the world for every collection), G1 (the default) and ZGC. Each child keeps
 * about 300 MB of live objects, replaces them at random, and runs a "hiccup" thread that sleeps 1 ms in a loop and
 * records how late it woke up. A late wake-up is time the thread was not allowed to run. The first column is the
 * longest pause the JVM's own GC log reports. Takes about 10 s; the numbers vary with your CPU and what else runs.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l04.demo.GcPauseDemoKt -q
 */
fun main(args: Array<String>) {
    if (args.firstOrNull() == "child") return child()
    val java = ProcessHandle.current().info().command().orElse("java")
    val classpath = System.getProperty("java.class.path")
    println("collector   GC log: longest pause   your thread: longest stall   99.9th pct   stalls over 10 ms")
    for ((name, flag) in listOf("Serial" to "-XX:+UseSerialGC", "G1" to "-XX:+UseG1GC", "ZGC" to "-XX:+UseZGC")) {
        val gcLog = Files.createTempFile("gc-", ".log")
        val process = ProcessBuilder(
            java, "-Xms1g", "-Xmx1g", flag, "-Xlog:gc,gc+phases:file=$gcLog",
            "-cp", classpath, "sfz.dist.l04.demo.GcPauseDemoKt", "child",
        ).redirectErrorStream(true).start()
        val out = process.inputStream.bufferedReader().readText()
        process.waitFor(60, TimeUnit.SECONDS)
        // lines such as "GC(3) Pause Full (Allocation Failure) 840M->315M(989M) 379.735ms" or "Pause Mark Start 0.014ms"
        val longest = Files.readAllLines(gcLog).mapNotNull { pause.find(it)?.groupValues?.get(1)?.toDouble() }.maxOrNull() ?: 0.0
        Files.delete(gcLog)
        val (stall, p999, over10) = out.trim().split(" ")
        println("%-9s %18.3f ms %24.1f ms %10.1f ms %15s".format(name, longest, stall.toDouble(), p999.toDouble(), over10))
    }
}

private val pause = Regex("""Pause.* ([0-9.]+)ms$""")

/** The child: build a live set, churn it, and measure how late a 1 ms sleep wakes up. */
private fun child() {
    val live = arrayOfNulls<LongArray>(3_500_000)                 // 3.5 M objects of 80 bytes: about 300 MB
    for (i in live.indices) live[i] = LongArray(8)
    val lateness = mutableListOf<Double>()
    val running = AtomicBoolean(true)
    val hiccups = Thread {
        while (running.get()) {
            val t0 = System.nanoTime()
            Thread.sleep(1)
            lateness += (System.nanoTime() - t0) / 1e6 - 1.0     // how much longer than 1 ms the sleep took
        }
    }
    hiccups.start()
    val rnd = Random(42)
    val end = System.nanoTime() + 2_500_000_000L
    while (System.nanoTime() < end) {
        repeat(10_000) { live[rnd.nextInt(live.size)] = LongArray(8) }   // old objects become garbage
        Thread.onSpinWait()
    }
    running.set(false)
    hiccups.join()
    val sorted = lateness.sorted()
    println("${sorted.last()} ${sorted[(sorted.size * 0.999).toInt()]} ${sorted.count { it > 10 }}")   // the parent formats it
}
