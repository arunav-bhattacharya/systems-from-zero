package sfz.enc.l05

// Finished: fake outside systems that remember every side effect, so the tests can count them.
// None of this knows about Temporal. You don't change this file.

/** Thrown by an outside system when retrying can never help (no stock, a refused parcel). */
class PermanentFailure(val type: String, message: String) : RuntimeException(message)

/**
 * The card issuer. It records every charge and refund. With [honorKeys] it remembers each
 * idempotency key and answers a repeated key with the first result instead of acting again,
 * the way Stripe's API does. With `honorKeys = false` every call is a new charge.
 */
class Bank(private val honorKeys: Boolean = true) {
    data class Charge(val id: String, val orderId: String, val amountCents: Long)

    private val seen = HashMap<String, String>()
    private val charges = ArrayList<Charge>()
    private val refunds = ArrayList<Charge>()

    @Synchronized
    fun charge(key: String, orderId: String, amountCents: Long): String {
        if (honorKeys) seen[key]?.let { return it }
        val id = "ch_${charges.size + 1}"
        charges += Charge(id, orderId, amountCents)
        seen[key] = id
        return id
    }

    @Synchronized
    fun refund(key: String, chargeId: String) {
        if (honorKeys && seen.containsKey(key)) return
        refunds += charges.first { it.id == chargeId }
        seen[key] = chargeId
    }

    /** How many times this order's card was charged. */
    @Synchronized
    fun chargesFor(orderId: String): Int = charges.count { it.orderId == orderId }

    /** Money taken for this order minus money given back. */
    @Synchronized
    fun netCents(orderId: String): Long =
        charges.filter { it.orderId == orderId }.sumOf { it.amountCents } -
            refunds.filter { it.orderId == orderId }.sumOf { it.amountCents }
}

/** Stock per SKU, and the units held for orders. */
class Warehouse(stock: Map<String, Int>) {
    private val onShelf = HashMap(stock)
    private val held = HashMap<String, String>() // reservation id -> sku
    private val seen = HashMap<String, String>()

    @Synchronized
    fun reserve(key: String, orderId: String, sku: String): String {
        seen[key]?.let { return it }
        val left = onShelf[sku] ?: 0
        if (left == 0) throw PermanentFailure("OutOfStock", "no $sku left for $orderId")
        onShelf[sku] = left - 1
        val id = "res_${orderId}_$sku"
        held[id] = sku
        seen[key] = id
        return id
    }

    @Synchronized
    fun release(key: String, reservationId: String) {
        if (seen.containsKey(key)) return
        val sku = held.remove(reservationId) ?: return
        onShelf[sku] = (onShelf[sku] ?: 0) + 1
        seen[key] = reservationId
    }

    @Synchronized
    fun onShelf(sku: String): Int = onShelf[sku] ?: 0
}

/** Takes parcels, unless it was told to refuse them. */
class Courier(private val refuse: Boolean = false) {
    private val parcels = ArrayList<String>()
    private val seen = HashMap<String, String>()

    @Synchronized
    fun ship(key: String, orderId: String): String {
        seen[key]?.let { return it }
        if (refuse) throw PermanentFailure("Refused", "the courier does not deliver to the address of $orderId")
        parcels += orderId
        val tracking = "trk_${parcels.size}"
        seen[key] = tracking
        return tracking
    }

    @Synchronized
    fun parcels(): List<String> = parcels.toList()
}

/** Everything outside the workflow. Orders above [fraudLimitCents] fail the fraud check. */
class World(
    val bank: Bank = Bank(),
    val warehouse: Warehouse = Warehouse(mapOf("sku-1" to 10)),
    val courier: Courier = Courier(),
    val fraudLimitCents: Long = 100_000,
)
