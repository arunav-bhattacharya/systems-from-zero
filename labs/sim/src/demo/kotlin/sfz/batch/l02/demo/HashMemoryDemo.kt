package sfz.batch.l02.demo

/**
 * How much memory does a HashMap<String, Long> of path counts really take on this JVM, and where
 * does it run out? Part 1 counts distinct payment paths and measures the heap per entry. Part 2
 * starts a second JVM with a 64 MB heap and keeps adding new paths until it throws OutOfMemoryError.
 */
fun main(args: Array<String>) {
    if (args.firstOrNull() == "child") return untilOutOfMemory()

    val rt = Runtime.getRuntime()
    fun usedAfterGc(): Long {
        repeat(3) { System.gc(); Thread.sleep(50) }
        return rt.totalMemory() - rt.freeMemory()
    }
    val keys = 1_000_000
    val before = usedAfterGc()
    val counts = HashMap<String, Long>()
    for (i in 0 until keys) counts.merge("/v1/payments/pay_%07d".format(i), 1L, Long::plus)   // 24-byte keys
    val after = usedAfterGc()
    println("%,d distinct 24-byte paths: about %,d MB of heap, %d bytes per entry".format(
        counts.size, (after - before) / 1_000_000, (after - before) / counts.size))

    // part 2: the same loop in a JVM that only has 64 MB of heap
    val java = ProcessHandle.current().info().command().orElse("java")
    val child = ProcessBuilder(java, "-Xmx64m", "-cp", System.getProperty("java.class.path"),
        "sfz.batch.l02.demo.HashMemoryDemoKt", "child")
        .redirectErrorStream(true).start()
    child.inputStream.bufferedReader().forEachLine(::println)
    child.waitFor()
    check(counts.size == keys)   // keep the map alive until here, so the measurement above holds
}

private fun untilOutOfMemory() {
    val counts = HashMap<String, Long>()
    var i = 0
    try {
        while (true) {
            counts.merge("/v1/payments/pay_%07d".format(i), 1L, Long::plus)
            i++
        }
    } catch (e: OutOfMemoryError) {
        val n = counts.size
        counts.clear()                                     // free the heap so we can print
        println("-Xmx64m: OutOfMemoryError after %,d distinct paths (%s)".format(n, e.message))
    }
}
