package sfz.found.l01

/** What the index knows about one payment: who took it, how much was authorized, and what happened last. */
data class PaymentState(val merchant: String, val amountCents: Long, val status: Kind)

/**
 * An index: payment id to its current state, so a lookup touches one entry instead of the whole log.
 */
class PaymentIndex : View {
    private val byId = HashMap<String, PaymentState>()

    override fun apply(e: PaymentEvent) {
        when (e.kind) {
            // the authorization creates the entry and fixes the amount
            Kind.AUTHORIZED -> byId[e.paymentId] = PaymentState(e.merchant, e.amountCents, Kind.AUTHORIZED)
            // later events only move the status on; log order guarantees the last one wins
            Kind.CAPTURED, Kind.REFUNDED -> byId[e.paymentId]?.let { byId[e.paymentId] = it.copy(status = e.kind) }
        }
    }

    override fun clear() = byId.clear()

    fun get(paymentId: String): PaymentState? = byId[paymentId]

    val size: Int get() = byId.size
}

/**
 * A materialized view: the net money each merchant took on each day. A capture adds its amount on
 * the day of the capture; a refund takes its amount off on the day of the refund. An authorization
 * moves no money.
 */
class DailyTotals : View {
    private val totals = HashMap<Pair<String, String>, Long>()

    override fun apply(e: PaymentEvent) {
        val delta = when (e.kind) {
            Kind.AUTHORIZED -> return
            Kind.CAPTURED -> e.amountCents
            Kind.REFUNDED -> -e.amountCents
        }
        totals.merge(e.merchant to e.day, delta, Long::plus)
    }

    override fun clear() = totals.clear()

    fun total(merchant: String, day: String): Long = totals[merchant to day] ?: 0L
}

/**
 * A cache in front of a slow computation: a merchant's all-time balance, which [loader] works out
 * by reading the whole log. The cache keeps each answer until an event for that merchant arrives.
 */
class BalanceCache(private val loader: (merchant: String) -> Long) : View {
    private val cached = HashMap<String, Long>()

    /** How many times the slow [loader] ran. The tests read it. */
    var loads: Int = 0
        private set

    fun get(merchant: String): Long =
        cached.getOrPut(merchant) {
            loads++                      // a miss: pay for the slow path once
            loader(merchant)
        }

    // a new event makes this merchant's cached answer wrong, so forget it; the next get reloads
    override fun apply(e: PaymentEvent) {
        cached.remove(e.merchant)
    }

    // a rebuilt cache is an empty cache: it fills up again on demand
    override fun clear() = cached.clear()
}

/**
 * Throws away everything in [views] and builds them again from the log: clear each one, then
 * replay the whole log once, in order, handing every event to every view.
 */
fun rebuild(log: PaymentLog, vararg views: View) {
    for (v in views) v.clear()           // without this, a second rebuild would count everything twice
    log.replay { _, e -> for (v in views) v.apply(e) }
}
