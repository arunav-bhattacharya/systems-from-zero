package sfz.batch.l01.demo

/** Splits the same CSV scan across 1, 2, 4, 8 and all cores, and prints the speedup. */
fun main() {
    PaymentFiles.open().use { c ->
        val sql = "SELECT count(*), sum(amount_cents) FROM read_csv('${PaymentFiles.csv.absolutePath}')"
        val cores = Runtime.getRuntime().availableProcessors()
        var oneThread = 0.0
        for (threads in listOf(1, 2, 4, 8, cores).distinct().sorted()) {
            c.createStatement().use { it.execute("SET threads = $threads") }   // DuckDB splits the file into chunks per thread
            val seconds = PaymentFiles.bestSeconds(c, sql)
            if (threads == 1) oneThread = seconds
            println("%2d threads: %.2f s   speedup %.1fx".format(threads, seconds, oneThread / seconds))
        }
    }
}
