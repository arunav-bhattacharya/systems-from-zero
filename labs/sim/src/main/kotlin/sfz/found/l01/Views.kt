package sfz.found.l01

/** What the index knows about one payment: who took it, how much was authorized, and what happened last. */
data class PaymentState(val merchant: String, val amountCents: Long, val status: Kind)

/**
 * An index: payment id to its current state, so a lookup touches one entry instead of the whole log.
 */
class PaymentIndex : View {
    private val byId = HashMap<String, PaymentState>()

    /**
     * AUTHORIZED creates the entry with the merchant and the amount. CAPTURED and REFUNDED keep the
     * entry and change only its status. Ignore a CAPTURED or REFUNDED for an id you have never seen.
     */
    override fun apply(e: PaymentEvent) {
        TODO("put or update the entry for e.paymentId")
    }

    override fun clear() = byId.clear()

    /** The current state of a payment, or null if the log has never mentioned it. */
    fun get(paymentId: String): PaymentState? = TODO("look the payment up")

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
        TODO("add captures, subtract refunds, ignore authorizations")
    }

    override fun clear() = totals.clear()

    /** Net cents for one merchant on one day; 0 if nothing moved. */
    fun total(merchant: String, day: String): Long = TODO("read the total")
}

/**
 * A cache in front of a slow computation: a merchant's all-time balance, which [loader] works out
 * by reading the whole log. The cache keeps each answer until an event for that merchant arrives.
 */
class BalanceCache(private val loader: (merchant: String) -> Long) : View {
    private val cached = HashMap<String, Long>()

    /** How many times the slow [loader] ran. Add one every time you call it. The tests read it. */
    var loads: Int = 0
        private set

    /** The cached balance, or, on a miss, call [loader], count the load, remember the answer and return it. */
    fun get(merchant: String): Long = TODO("return the cached answer or load it")

    /** A new event makes this merchant's cached answer wrong. Forget it (and only it). */
    override fun apply(e: PaymentEvent) {
        TODO("invalidate e.merchant")
    }

    override fun clear() = cached.clear()
}

/**
 * Throws away everything in [views] and builds them again from the log: clear each one, then
 * replay the whole log once, in order, handing every event to every view.
 */
fun rebuild(log: PaymentLog, vararg views: View) {
    TODO("clear every view, then replay the log into all of them")
}
