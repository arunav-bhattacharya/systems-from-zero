package sfz.stream.l07.demo

/**
 * 1,000 payments arrive, one per virtual ms, and the job writes one output row per payment. It crashes just after
 * payment 950 and restarts from what it committed. Two designs:
 *
 * - record at a time: write each row at once, commit the input offset after every 100 records (at-least-once).
 * - micro-batches of 100 ms: keep a batch's rows in memory, then make the rows and the batch's end offset durable
 *   in one step (Spark writes the batch's output, then its commit-log entry). A crash mid-batch leaves nothing of it.
 */
fun main() {
    val payments = 1_000
    val crashAfter = 950

    // record at a time
    val rows = mutableListOf<Int>()                 // durable: what the world sees
    var committed = 0                               // durable: the committed offset
    var crashed = false
    var p = 0
    while (p < payments) {
        if (!crashed && p > crashAfter) { crashed = true; p = committed; continue }   // crash, restart from the offset
        rows += p
        if ((p + 1) % 100 == 0) committed = p + 1
        p++
    }
    println("record at a time: ${rows.size} rows for $payments payments, ${rows.size - rows.toSet().size} duplicates, " +
        "a row is visible right after its payment")

    // micro-batches of 100 ms
    val visible = mutableListOf<Int>()              // durable: what the world sees
    var batchEnd = 0                                // durable: the commit log, the end offset of the last batch
    var waited = 0L
    crashed = false
    var start = 0
    while (start < payments) {
        val end = minOf(start + 100, payments)
        val batch = mutableListOf<Int>()            // in memory until the batch commits
        for (q in start until end) {
            if (!crashed && q > crashAfter) { crashed = true; break }
            batch += q
        }
        if (batch.size < end - start) {
            println("crash in the batch [$start, $end): ${batch.size} rows in memory are lost; rerun the batch from offset $batchEnd")
            start = batchEnd
            continue
        }
        visible += batch                            // the batch's rows and its commit entry: one step
        batchEnd = end
        waited += batch.sumOf { (end - it).toLong() } // payment q arrives at q ms and shows up when the batch ends
        start = end
    }
    println("micro-batches:    ${visible.size} rows for $payments payments, ${visible.size - visible.toSet().size} duplicates, " +
        "a row is visible %.1f ms after its payment on average".format(waited.toDouble() / payments))
}
