package sfz.batch.l01.demo

/** Times one CPU core scanning a CSV file, then turns that speed into "how long for 1 TB". */
fun main() {
    PaymentFiles.open().use { c ->
        c.createStatement().use { it.execute("SET threads = 1") }        // one reader, like one disk
        val csv = PaymentFiles.csv
        val sql = "SELECT count(*), sum(amount_cents) FROM read_csv('${csv.absolutePath}')"
        val seconds = PaymentFiles.bestSeconds(c, sql)
        val bytesPerSecond = csv.length() / seconds
        println("file:      ${csv.name}, ${PaymentFiles.mb(csv.length())}, %,d rows".format(PaymentFiles.ROWS))
        println("one core:  %.2f s, so about %s per second".format(seconds, PaymentFiles.mb(bytesPerSecond.toLong())))
        println("1 TB at that speed: about %.0f minutes".format(1e12 / bytesPerSecond / 60))
    }
}
