package sfz.derive.l05.demo

import kotlin.math.pow

// The shape of the bug Meta found (Dixit et al., 2021), made small. A nightly job unpacks 1,000
// compressed files on a 64-core machine. Before unpacking, it computes each file's size from a
// formula that calls pow(1.1, level). Core 59 is defective: it returns 0 for pow(1.1, 53) and the
// right answer for everything else. A file whose size comes out as 0 is "empty" and is skipped.

private fun pow(core: Int, x: Double, y: Double): Double =
    if (core == 59 && x == 1.1 && y == 53.0) 0.0 else x.pow(y)        // a mercurial core: wrong, and silent

fun main() {
    val levels = (0 until 1_000).map { 40 + (it * 7919) % 21 }         // compression level 40..60 per file
    val written = ArrayList<Int>()
    for ((file, level) in levels.withIndex()) {
        val core = file % 64                                             // the scheduler spreads files over cores
        val size = pow(core, 1.1, level.toDouble()).toInt() * 4_096
        if (size == 0) continue                                          // "nothing to unpack"
        written += file
    }
    println("job: unpacked ${written.size} files, exit code 0, no errors logged")

    // the check that catches it: count what came out against what went in, file by file
    val missing = levels.indices.filter { it !in written.toSet() }
    println("audit: ${levels.size} files in, ${written.size} files out, ${missing.size} missing")
    for (f in missing) println("  file $f: level ${levels[f]}, unpacked on core ${f % 64}")
    println("pow(1.1, 53) on a good core = ${1.1.pow(53).toInt()}, on core 59 = ${pow(59, 1.1, 53.0).toInt()}")
}
