package sfz.bigdata.l12.demo

import com.sun.management.OperatingSystemMXBean
import java.io.File
import java.lang.management.ManagementFactory

/**
 * Measures the two numbers the engine rubric needs from this laptop: how fast DuckDB decodes
 * Parquet on one core and on all of them. Then works out, for five workloads of a payments
 * company, the bytes each reads after pruning and the seconds it would take here and on a
 * 64-core cloud VM that reads object storage at 1.5 GB/s.
 */
fun main() {
    freshDemoDir()
    val cores = Runtime.getRuntime().availableProcessors()
    val memory = (ManagementFactory.getOperatingSystemMXBean() as OperatingSystemMXBean).totalMemorySize
    println("this machine: $cores cores, %.0f GiB of memory".format(memory / (1L shl 30).toDouble()))

    val c = duck()
    val payments = File(DEMO_DIR, "payments")
    writePayments(c, 10_000_000, payments, File(DEMO_DIR, "merchants"))
    val glob = "${payments.absolutePath}/*.parquet"
    // the compressed bytes of the two columns the query needs, from the Parquet footers (lesson 4)
    val bytes = (c.rows("SELECT sum(total_compressed_size) FROM parquet_metadata('$glob') " +
        "WHERE path_in_schema IN ('amount_cents', 'status')").first()[0] as Number).toLong()
    val query = "SELECT status, sum(amount_cents) FROM read_parquet('$glob') GROUP BY status"
    fun bestMillis(threads: Int): Double {
        c.run("SET threads = $threads")
        return (1..5).minOf {
            val t0 = System.nanoTime()
            c.rows(query)
            (System.nanoTime() - t0) / 1e6
        }
    }
    val one = bestMillis(1)
    val all = bestMillis(cores)
    val perCore = bytes / (one / 1000)
    val allCores = bytes / (all / 1000)
    println("DuckDB, sum by status over 10,000,000 payments (2 columns, %.0f MB compressed, files in the page cache):".format(bytes / 1e6))
    println("   1 thread:  %5.0f ms, so about %.0f MB/s per core".format(one, perCore / 1e6))
    println("  %2d threads: %5.0f ms, so about %.1f GB/s".format(cores, all, allCores / 1e9))

    // four TB of payments over 3 years (1,095 days), 60 columns of similar size
    data class W(val name: String, val days: Int, val columns: Int, val users: Int)
    val workloads = listOf(
        W("monthly finance report", 30, 4, 1),
        W("one merchant's disputes, ad hoc", 365, 6, 1),
        W("merchant dashboard, 40 users", 90, 4, 40),
        W("nightly settlement over a week", 7, 12, 1),
        W("fraud feature backfill, 3 years", 1095, 30, 1),
    )
    val vm = 1.5e9
    println("%-34s %10s %12s %12s".format("workload (4 TB table)", "reads", "this laptop", "cloud VM"))
    for (w in workloads) {
        val read = 4e12 * w.days / 1095 * w.columns / 60
        println("%-34s %7.1f GB %10.1f s %10.1f s".format(w.name, read / 1e9, read / allCores * w.users, read / vm * w.users))
    }
    c.close()
}
