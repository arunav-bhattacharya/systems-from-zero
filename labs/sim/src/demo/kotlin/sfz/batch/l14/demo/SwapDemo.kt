package sfz.batch.l14.demo

import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption

/**
 * Three nights of a serving store built by a batch job: a good build, a build that crashes
 * halfway, and a build with bad scores that is published and then rolled back. Prints the folder
 * and what a reader gets after each step.
 */
fun main() {
    val root = File("build/l14/store").apply { deleteRecursively(); mkdirs() }
    val current = File(root, "CURRENT")
    fun publish(v: String) {
        val tmp = File(root, "CURRENT.tmp").apply { writeText(v) }
        Files.move(tmp.toPath(), current.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
    }
    fun build(v: String, score: Int, crashAfter: Int = Int.MAX_VALUE) {
        val dir = File(root, v).apply { mkdirs() }
        File(dir, "data").bufferedWriter().use { w ->
            for (m in 0 until 1_000) {
                if (m == crashAfter) throw IllegalStateException("executor lost while writing $v")
                w.write("merchant-%04d\t$score\n".format(m))
            }
        }
    }
    fun read(): String {
        val v = current.readText()
        val line = File(root, "$v/data").readLines().first { it.startsWith("merchant-0042\t") }
        return "CURRENT=$v, merchant-0042 scores ${line.substringAfter('\t')}"
    }
    fun show(step: String) {
        val folders = root.list()!!.filter { it.startsWith("v") }.sorted().joinToString { v ->
            "$v (${File(root, "$v/data").readLines().size} lines)"
        }
        println("$step\n  folders: $folders\n  a reader: ${read()}")
    }

    build("v1", 17); publish("v1"); show("night 1: build v1, publish")
    runCatching { build("v2", 18, crashAfter = 400) }.onFailure { println("night 2: the build failed: ${it.message}") }
    show("  nothing was published")
    build("v3", 0); publish("v3"); show("night 3: build v3 with a bug (every score 0), publish")
    publish("v1"); show("rollback: publish v1 again")
}
