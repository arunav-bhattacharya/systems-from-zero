package sfz.found.l01.demo

import kotlin.random.Random

/**
 * Two questions about the same two million payments. The operational one touches one row. The
 * analytical one touches every row, and runs faster when each field is stored as its own column.
 */
private class Payment(
    val id: Int, val merchant: Int, val category: Int, val week: Int, val amountCents: Long, val refunded: Boolean,
    // the other fields a real payment row carries; the analytical question needs none of them
    val customerId: Long, val cardBin: Int, val country: Int, val currency: Int, val createdAt: Long, val capturedAt: Long,
    val terminalId: Long, val authCode: Long, val feeCents: Long, val riskScore: Int, val settlementBatch: Long,
)

private const val N = 2_000_000
private const val CATEGORIES = 8
private const val WEEKS = 104

fun main() {
    val rnd = Random(7)

    // row layout: one object per payment, all of its fields together
    val rows = ArrayList<Payment>(N)
    for (i in 0 until N) {
        val category = rnd.nextInt(CATEGORIES)
        rows += Payment(
            i, rnd.nextInt(20_000), category, rnd.nextInt(WEEKS), 100L * rnd.nextInt(1, 500), rnd.nextInt(100) < 2 + category,
            rnd.nextLong(), rnd.nextInt(), rnd.nextInt(200), rnd.nextInt(30), rnd.nextLong(), rnd.nextLong(),
            rnd.nextLong(), rnd.nextLong(), rnd.nextLong(100), rnd.nextInt(100), rnd.nextLong(),
        )
    }
    // column layout: one array per field, all values of that field together
    val categoryCol = IntArray(N) { rows[it].category }
    val weekCol = IntArray(N) { rows[it].week }
    val refundedCol = BooleanArray(N) { rows[it].refunded }

    // operational: what happened to one payment? (the id is the position, so this is a perfect index)
    val ids = IntArray(100_000) { rnd.nextInt(N) }
    var sink = 0L
    repeat(3) { for (id in ids) sink += rows[id].amountCents }          // warm up
    val t0 = System.nanoTime()
    for (id in ids) sink += rows[id].amountCents
    val lookupNs = (System.nanoTime() - t0).toDouble() / ids.size
    val p = rows[1_234_567]
    println("operational: payment ${p.id} -> merchant ${p.merchant}, %.2f, refunded=${p.refunded}".format(p.amountCents / 100.0))
    println("             1 row touched, about %.0f ns per lookup (average of %,d)".format(lookupNs, ids.size) + if (sink == 42L) "!" else "")

    // analytical: refund rate per category per week, over two years of payments
    fun byRows(): Array<IntArray> {
        val total = Array(CATEGORIES) { IntArray(WEEKS) }
        val refunds = Array(CATEGORIES) { IntArray(WEEKS) }
        for (r in rows) {
            total[r.category][r.week]++
            if (r.refunded) refunds[r.category][r.week]++
        }
        return arrayOf(total[2], refunds[2])
    }
    fun byColumns(): Array<IntArray> {
        val total = Array(CATEGORIES) { IntArray(WEEKS) }
        val refunds = Array(CATEGORIES) { IntArray(WEEKS) }
        for (i in 0 until N) {
            total[categoryCol[i]][weekCol[i]]++
            if (refundedCol[i]) refunds[categoryCol[i]][weekCol[i]]++
        }
        return arrayOf(total[2], refunds[2])
    }
    fun bestOf(times: Int, f: () -> Array<IntArray>): Pair<Double, Array<IntArray>> {
        var best = Double.MAX_VALUE
        var out = f()
        repeat(times) {
            val t = System.nanoTime(); out = f(); best = minOf(best, (System.nanoTime() - t) / 1e6)
        }
        return best to out
    }
    val (rowMs, r) = bestOf(5, ::byRows)
    val (colMs, _) = bestOf(5, ::byColumns)
    println("analytical:  refund rate per category per week, $CATEGORIES categories x $WEEKS weeks")
    println("             %,d rows touched".format(N))
    println("             row layout    %.1f ms".format(rowMs))
    println("             column layout %.1f ms".format(colMs))
    println("             e.g. category 2, week 52: %.1f%% of %,d payments refunded".format(100.0 * r[1][52] / r[0][52], r[0][52]))
}
