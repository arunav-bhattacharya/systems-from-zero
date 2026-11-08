package sfz.derive.l01

/**
 * v1, the table the dashboard reads today (given). Gross captured cents per merchant per day.
 *
 * It ignores refunds, which is why finance wants v2, and it buckets by [processedAt], the minute
 * the job saw the payment. On the live path that is almost always the minute the payment
 * happened, so nobody noticed for months. A payment uploaded late lands on the day it arrived.
 */
class DailyGross : View {
    private val totals = HashMap<Pair<String, Long>, Long>()

    override fun apply(r: Record, processedAt: Long) {
        val e = r.event
        if (e.kind == Kind.CAPTURED) totals.merge(e.merchant to dayOf(processedAt), e.cents, Long::plus)
    }

    override fun cents(merchant: String, day: Long): Long = totals[merchant to day] ?: 0

    override fun clear() = totals.clear()
}

/**
 * v2: net revenue per merchant per day. A capture adds its cents, a refund takes its cents off.
 *
 * TODO: the body below copies v1's habit of bucketing by [processedAt]. Run the tests and look
 * at what that does to a replay of 30 days of history. Then make each record count on the day
 * the payment happened, which the record itself carries, so the answer no longer depends on when
 * the job ran.
 */
class DailyNet : View {
    private val totals = HashMap<Pair<String, Long>, Long>()

    override fun apply(r: Record, processedAt: Long) {
        val e = r.event
        val delta = if (e.kind == Kind.CAPTURED) e.cents else -e.cents
        totals.merge(e.merchant to dayOf(processedAt), delta, Long::plus)
    }

    override fun cents(merchant: String, day: Long): Long = totals[merchant to day] ?: 0

    override fun clear() = totals.clear()
}
