package sfz.internals.l09

/** How many rows a batch holds at most. DuckDB's vectors hold 2,048 values; the idea is the same. */
const val BATCH_SIZE = 1024

/**
 * Up to [BATCH_SIZE] rows, stored by column: `columns[c][i]` is column `c` of row `i`, for `i < size`.
 * Every column is a plain `LongArray`, so an operator can work through one column in a tight loop.
 */
class Batch(val columns: List<LongArray>, val size: Int) {
    /** Row [i] as a list, to compare with the row-at-a-time operators. */
    fun row(i: Int): Row = columns.map { it[i] }
}

/** The vectorized version of [Operator]: [nextBatch] returns up to [BATCH_SIZE] rows, or null at the end. */
interface BatchOperator {
    fun open()
    fun nextBatch(): Batch?
    fun close()
}

/** Cuts columns (all of the same length) into batches of [batchSize] rows. */
class BatchScan(private val columns: List<LongArray>, private val batchSize: Int = BATCH_SIZE) : BatchOperator {
    private val rows = columns.firstOrNull()?.size ?: 0
    private var pos = -1
    override fun open() { pos = 0 }
    override fun nextBatch(): Batch? {
        check(pos >= 0) { "nextBatch() before open()" }
        if (pos >= rows) return null
        val end = minOf(pos + batchSize, rows)
        val b = Batch(columns.map { it.copyOfRange(pos, end) }, end - pos)
        pos = end
        return b
    }
    override fun close() { pos = -1 }
}

/**
 * `WHERE column > greaterThan`, one batch at a time. For each input batch: find the positions that pass
 * in one loop over that one column, then copy those positions of every column into the output batch.
 * Never returns an empty batch: if nothing in a batch passes, pull the next one.
 */
class BatchFilter(
    private val child: BatchOperator,
    private val column: Int,
    private val greaterThan: Long,
) : BatchOperator {
    override fun open() = child.open()
    override fun close() = child.close()

    override fun nextBatch(): Batch? {
        while (true) {
            val b = child.nextBatch() ?: return null
            val c = b.columns[column]
            val selected = IntArray(b.size)                      // the "selection vector"
            var n = 0
            for (i in 0 until b.size) {                          // one tight loop, no calls, no boxing
                if (c[i] > greaterThan) selected[n++] = i
            }
            if (n == 0) continue                                 // nothing passed: try the next batch
            return Batch(b.columns.map { col -> LongArray(n) { col[selected[it]] } }, n)
        }
    }
}
