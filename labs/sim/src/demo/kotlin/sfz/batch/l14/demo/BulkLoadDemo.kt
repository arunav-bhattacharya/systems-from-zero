package sfz.batch.l14.demo

import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread
import kotlin.random.Random

/**
 * Last night's batch job scored 1,000,000 merchants again. Two ways to get the new scores to the
 * service that reads them: write them one by one into the live store while it serves, or build a
 * new read-only file offline and switch to it in one step. A reader samples 1,000 merchants while
 * each runs.
 */
fun main() {
    val n = 1_000_000
    val keys = Array(n) { "merchant-%07d".format(it) }
    val pick = Random(1)
    val sample = (0 until 1_000).map { keys[pick.nextInt(n)] }

    // 1. row by row into the live store, in the order the job's tasks happen to finish
    val live = ConcurrentHashMap<String, String>(n * 2)
    keys.forEach { live[it] = "run-1" }
    val seen = mutableListOf<Int>()
    val writing = AtomicBoolean(true)
    val reader = thread {
        while (writing.get()) {
            seen += sample.count { live[it] == "run-2" }
            Thread.sleep(20)
        }
    }
    val t0 = System.nanoTime()
    for (i in keys.indices.shuffled(Random(2))) live[keys[i]] = "run-2"
    writing.set(false)
    reader.join()
    val inPlaceMs = (System.nanoTime() - t0) / 1e6
    val mixed = seen.filter { it in 1..999 }
    println("in place: %,d writes in %.0f ms; the reader looked %d times while it ran, and %d of those reads mixed both runs".format(
        n, inPlaceMs, seen.size, mixed.size))
    if (mixed.isNotEmpty()) println("  for example, %d of the 1,000 sampled merchants had new scores and %d still had old ones".format(mixed[mixed.size / 2], 1_000 - mixed[mixed.size / 2]))

    // 2. offline: write a sorted file in a new folder, then flip a pointer
    val root = File("build/l14/scores").apply { deleteRecursively(); mkdirs() }
    val t1 = System.nanoTime()
    val v2 = File(root, "v2").apply { mkdirs() }
    File(v2, "data").bufferedWriter().use { w -> for (k in keys.sorted()) { w.write(k); w.write("\trun-2\n") } }
    val buildMs = (System.nanoTime() - t1) / 1e6
    val tmp = File(root, "CURRENT.tmp").apply { writeText("v2") }
    val t2 = System.nanoTime()
    Files.move(tmp.toPath(), File(root, "CURRENT").toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
    val swapUs = (System.nanoTime() - t2) / 1e3
    println("offline: built a sorted file of %,d entries (%.1f MB) in %.0f ms, which no reader could see;".format(
        n, File(v2, "data").length() / 1e6, buildMs))
    println("  then the switch took %.0f microseconds: a reader sees run 1 or run 2, never both".format(swapUs))
}
