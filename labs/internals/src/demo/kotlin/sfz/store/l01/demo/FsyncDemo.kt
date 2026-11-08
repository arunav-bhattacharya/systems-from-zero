package sfz.store.l01.demo

import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.file.Files
import java.nio.file.StandardOpenOption.CREATE
import java.nio.file.StandardOpenOption.WRITE

/** Appends 1,000 records of 100 bytes three ways and times each: no force, force per record, force per batch. */
fun main(args: Array<String>) {
    val records = args.firstOrNull()?.toInt() ?: 1_000
    val batch = 50
    val dir = Files.createTempDirectory("sfz-fsync")
    val record = ByteArray(100) { 'x'.code.toByte() }

    fun run(label: String, forceEvery: Int) {
        val file = dir.resolve("$label.log")
        FileChannel.open(file, CREATE, WRITE).use { ch ->
            val t0 = System.nanoTime()
            for (i in 1..records) {
                ch.write(ByteBuffer.wrap(record))                      // lands in the OS page cache
                if (forceEvery > 0 && i % forceEvery == 0) ch.force(false) // waits for the disk
            }
            val ms = (System.nanoTime() - t0) / 1e6
            println("%-22s %,6d records in %8.1f ms  = %,10.0f records/s".format(label, records, ms, records / (ms / 1000)))
        }
    }

    run("write only", 0)
    run("force every record", 1)
    run("force every $batch", batch)
    dir.toFile().deleteRecursively()
}
