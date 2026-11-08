package sfz.cache.l01.demo

import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.file.Files
import java.nio.file.StandardOpenOption
import java.util.Random
import kotlin.concurrent.thread

/** Measures four rungs of the latency ladder from the JVM: CPU cache, RAM, the OS page cache, a loopback round trip. */
fun main() {
    println("pointer chase, 16 KB array (fits in the L1 cache): %8.1f ns per load".format(chase(16 shl 10, 50_000_000)))
    println("pointer chase, 4 MB array (an L2 or L3 cache):     %8.1f ns per load".format(chase(4 shl 20, 20_000_000)))
    println("pointer chase, 256 MB array (main memory):         %8.1f ns per load".format(chase(256 shl 20, 10_000_000)))
    println("4 KB read from a file the OS has cached:           %8.1f us per read".format(cachedFileRead() / 1_000))
    println("1-byte round trip over loopback TCP:               %8.1f us per round trip".format(loopbackRoundTrip() / 1_000))
}

/** Follows a random cycle through an int array, so every load depends on the one before: no prefetching helps. */
private fun chase(bytes: Int, steps: Int): Double {
    val n = bytes / 4
    val next = IntArray(n) { it }
    val random = Random(1)
    for (i in n - 1 downTo 1) {                         // Sattolo's shuffle: one cycle through every slot
        val j = random.nextInt(i)
        val t = next[i]; next[i] = next[j]; next[j] = t
    }
    var p = 0
    repeat(steps / 10) { p = next[p] }                  // warm up the JIT and the caches
    val t0 = System.nanoTime()
    repeat(steps) { p = next[p] }
    val ns = System.nanoTime() - t0
    if (p == -1) println()                              // use p, so the JIT can't drop the loop
    return ns.toDouble() / steps
}

/** Random 4 KB reads from a 64 MB file that was just written, so every block sits in the page cache. */
private fun cachedFileRead(): Double {
    val file = Files.createTempFile("sfz-ladder", ".bin")
    try {
        Files.write(file, ByteArray(64 shl 20))
        FileChannel.open(file, StandardOpenOption.READ).use { ch ->
            val buf = ByteBuffer.allocateDirect(4096)
            val random = Random(2)
            val blocks = (64 shl 20) / 4096
            repeat(20_000) { buf.clear(); ch.read(buf, random.nextInt(blocks).toLong() * 4096) }
            val reads = 200_000
            val t0 = System.nanoTime()
            repeat(reads) { buf.clear(); ch.read(buf, random.nextInt(blocks).toLong() * 4096) }
            return (System.nanoTime() - t0).toDouble() / reads
        }
    } finally {
        Files.delete(file)
    }
}

/** One byte to an echo server on the same machine and back: two trips through the kernel's network stack. */
private fun loopbackRoundTrip(): Double {
    ServerSocket(0, 1, InetAddress.getLoopbackAddress()).use { server ->
        val echo = thread {
            runCatching {
                server.accept().use { s ->
                    val inp = s.getInputStream()
                    val out = s.getOutputStream()
                    while (true) {
                        val b = inp.read()
                        if (b == -1) break
                        out.write(b)
                    }
                }
            }
        }
        try {
            Socket(InetAddress.getLoopbackAddress(), server.localPort).use { client ->
                client.tcpNoDelay = true
                val inp = client.getInputStream()
                val out = client.getOutputStream()
                repeat(5_000) { out.write(1); inp.read() }
                val trips = 20_000
                val t0 = System.nanoTime()
                repeat(trips) { out.write(1); inp.read() }
                return (System.nanoTime() - t0).toDouble() / trips
            }
        } finally {
            echo.join(1_000)
        }
    }
}
