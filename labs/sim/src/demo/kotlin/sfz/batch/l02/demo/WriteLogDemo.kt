package sfz.batch.l02.demo

import java.io.File

/**
 * Writes one day of a payments API's access log to build/l02/access.log (inside labs/sim), for the
 * shell Try its: 2,000,000 lines, paths drawn from 1,000,000 possible ones. The same file every run.
 */
fun main() {
    val file = File("build/l02/access.log").apply { parentFile.mkdirs() }
    val lines = 2_000_000
    val distinct = HashSet<String>()
    file.bufferedWriter().use { out ->
        for (line in AccessLog.lines(lines, distinctPaths = 1_000_000)) {
            out.write(line)
            out.newLine()
            distinct += line.split(' ')[6]                 // awk's $7
        }
    }
    println("wrote %s: %,d lines, %,d bytes, %,d distinct paths".format(file.path, lines, file.length(), distinct.size))
    println("first line: " + file.bufferedReader().use { it.readLine() })
}
