package sfz.found.l01.demo

import java.io.RandomAccessFile
import java.nio.file.Files
import kotlin.random.Random

/**
 * A payments service that keeps everything in one file, one payment per line.
 * Finding one payment means reading the file until you hit it. An index (payment id to the byte
 * where its line starts) turns that into one jump.
 */
fun main(args: Array<String>) {
    val n = args.firstOrNull()?.toInt() ?: 1_000_000     // try -Pargs=5000000
    val file = Files.createTempFile("payments", ".log")
    val rnd = Random(1)
    val merchants = listOf("m-cafe", "m-books", "m-bikes", "m-shoes", "m-hotel")

    // write one million payments, one line each
    Files.newBufferedWriter(file).use { w ->
        for (i in 1..n) {
            w.write("pay-%07d %s 2026-03-02 CAPTURED %d\n".format(i, merchants[rnd.nextInt(5)], 100 * rnd.nextInt(1, 500)))
        }
    }
    println("file: %,d payments, %.1f MB".format(n, Files.size(file) / 1e6))
    println(Files.newBufferedReader(file).use { it.readLine() })

    val target = "pay-%07d".format(n)

    // 1. no index: read lines until the id matches (best of 3 runs, so the JIT has warmed up)
    var scanMs = Double.MAX_VALUE
    var found = ""
    repeat(3) {
        val t0 = System.nanoTime()
        found = Files.newBufferedReader(file).useLines { lines -> lines.first { it.startsWith(target) } }
        scanMs = minOf(scanMs, (System.nanoTime() - t0) / 1e6)
    }
    println("scan:   found $target after reading every line: %.0f ms".format(scanMs))

    // 2. build an index once: id -> byte offset of the line
    val t1 = System.nanoTime()
    val index = HashMap<String, Long>(n * 2)
    var offset = 0L
    Files.newBufferedReader(file).useLines { lines ->
        for (line in lines) {
            index[line.substring(0, 11)] = offset
            offset += line.length + 1
        }
    }
    println("index:  built for %,d ids in %.0f ms".format(index.size, (System.nanoTime() - t1) / 1e6))

    // 3. with the index: one hash lookup, one seek, one read of a few bytes
    RandomAccessFile(file.toFile(), "r").use { raf ->
        val buf = ByteArray(64)
        fun lineAt(pos: Long): String {
            raf.seek(pos)
            val len = raf.read(buf)
            return String(buf, 0, len).substringBefore('\n')
        }
        val ids = List(10_000) { "pay-%07d".format(rnd.nextInt(1, n + 1)) }
        repeat(3) { ids.forEach { lineAt(index.getValue(it)) } }   // warm up
        val t2 = System.nanoTime()
        ids.forEach { lineAt(index.getValue(it)) }
        val perLookupUs = (System.nanoTime() - t2) / 1e3 / ids.size
        println("lookup: ${lineAt(index.getValue(target))} in %.1f µs each (average of %,d)".format(perLookupUs, ids.size))
        println("speed-up: about %,.0fx".format(scanMs * 1000 / perLookupUs))
    }
    Files.delete(file)
}
