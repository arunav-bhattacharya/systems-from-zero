package sfz.shard.l01

/** A tenant of a multitenant payments platform: one merchant and its peak load. */
data class Tenant(val id: String, val paymentsPerSecond: Double)

/** Where each tenant runs. A cell is a full copy of the stack (services and storage) for some tenants. */
object TenantPlacement {
    /** The thin router's rule: hash the tenant id, take it mod the number of cells. Given. */
    fun byHash(tenants: List<Tenant>, cells: Int): Map<String, Int> =
        tenants.associate { it.id to Math.floorMod(stableHash(it.id), cells.toLong()).toInt() }

    /**
     * A placement that knows how big each tenant is.
     *
     * 1. Every tenant with at least [dedicatedAt] payments a second gets a cell of its own: the biggest
     *    takes cell 0, the next cell 1, and so on.
     * 2. The other tenants share the remaining cells. Take them biggest first (ties by id) and put each
     *    on the shared cell with the least load so far (ties go to the lower cell number).
     *
     * Returns tenant id -> cell number.
     */
    fun bySize(tenants: List<Tenant>, cells: Int, dedicatedAt: Double): Map<String, Int> {
        TODO("dedicated cells for the big tenants, then biggest-first onto the least-loaded shared cell")
    }

    /** Payments a second on each cell. Given. */
    fun cellLoads(placement: Map<String, Int>, tenants: List<Tenant>, cells: Int): DoubleArray {
        val loads = DoubleArray(cells)
        for (t in tenants) loads[placement.getValue(t.id)] += t.paymentsPerSecond
        return loads
    }

    /** How many other tenants share [tenantId]'s cell: everyone a noisy neighbour can slow down. Given. */
    fun neighbours(placement: Map<String, Int>, tenantId: String): Int {
        val cell = placement.getValue(tenantId)
        return placement.count { (id, c) -> c == cell && id != tenantId }
    }
}

/** Merchants whose sizes follow a Zipf curve: the k-th biggest takes a share proportional to 1/k. Given. */
object Merchants {
    fun zipf(count: Int, totalPaymentsPerSecond: Double): List<Tenant> {
        val harmonic = (1..count).sumOf { 1.0 / it }
        return (1..count).map { k -> Tenant("T-%04d".format(k), totalPaymentsPerSecond / (k * harmonic)) }
    }
}
