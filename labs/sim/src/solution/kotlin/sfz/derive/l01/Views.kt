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
 * Each record counts on the day the payment happened, so a replay a month later gives the same
 * table as the live path did.
 */
class DailyNet : View {
    private val totals = HashMap<Pair<String, Long>, Long>()

    override fun apply(r: Record, processedAt: Long) {
        val e = r.event
        val delta = if (e.kind == Kind.CAPTURED) e.cents else -e.cents
        // event time: the minute the payment happened, carried inside the record.
        // processedAt is when this job ran, which during a replay is "today" for every record.
        totals.merge(e.merchant to dayOf(e.eventTime), delta, Long::plus)
    }

    override fun cents(merchant: String, day: Long): Long = totals[merchant to day] ?: 0

    override fun clear() = totals.clear()
}
