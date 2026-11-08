package sfz.repl.l08

/** How two versions relate: one came before the other, they are the same, or neither saw the other. */
enum class Order { BEFORE, AFTER, EQUAL, CONCURRENT }

/**
 * A vector clock: one counter per node that has coordinated a write of this value, as in Dynamo.
 * A node that isn't listed counts as 0. Immutable: every operation returns a new clock.
 *
 * Your job: [compare] and [merge].
 */
data class VectorClock(val counters: Map<String, Long> = emptyMap()) {
    operator fun get(node: String): Long = counters[node] ?: 0

    /** This clock with [node]'s counter one higher: what a node does when it coordinates a write. Given. */
    fun increment(node: String): VectorClock = VectorClock(counters + (node to this[node] + 1))

    /**
     * How this clock relates to [other]. Look at every node in either clock:
     *
     * - every counter equal: [Order.EQUAL];
     * - every counter here <= the one in [other], at least one smaller: [Order.BEFORE]
     *   (this version is an ancestor of the other: the other saw it);
     * - every counter here >= the one in [other], at least one bigger: [Order.AFTER];
     * - some smaller and some bigger: [Order.CONCURRENT] (neither saw the other: a conflict).
     */
    fun compare(other: VectorClock): Order {
        var smaller = false
        var bigger = false
        for (node in counters.keys + other.counters.keys) {
            if (this[node] < other[node]) smaller = true
            if (this[node] > other[node]) bigger = true
        }
        return when {
            smaller && bigger -> Order.CONCURRENT
            smaller -> Order.BEFORE
            bigger -> Order.AFTER
            else -> Order.EQUAL
        }
    }

    /** The clock that has seen everything both have seen: for each node, the bigger counter. */
    fun merge(other: VectorClock): VectorClock {
        val nodes = counters.keys + other.counters.keys
        return VectorClock(nodes.associateWith { maxOf(this[it], other[it]) })
    }

    /** Dynamo's notation: `[(Sx, 2), (Sy, 1)]`. Given. */
    override fun toString(): String = counters.toSortedMap().entries.joinToString(", ", "[", "]") { "(${it.key}, ${it.value})" }
}

/** One version of a value and the clock that says what it has seen. */
data class Version(val value: String, val clock: VectorClock)

/**
 * One key on one Dynamo replica. It keeps every version that no other version it holds descends
 * from: usually one, several ("siblings") after concurrent writes. A read returns them all; the
 * client merges them and writes the result back with [context], which then replaces them.
 *
 * Your job: [put]. [receive], [context] and [prune] are given.
 */
class DynamoKey {
    /** The versions this replica holds for the key, oldest write first. */
    var versions: List<Version> = emptyList()
        private set

    /**
     * A client's write of [value], coordinated by [node]. [context] is the clock of what the client
     * read before writing (an empty clock for a blind first write).
     *
     * 1. The new version's clock is `context.increment(node)`: it has seen everything the client
     *    read, plus this one new write.
     * 2. Keep only what [prune] keeps of the stored versions plus the new one. Versions the new
     *    clock descends from disappear; concurrent ones stay as siblings.
     * 3. Return the new version.
     *
     * (A real coordinator also makes sure its own counter never goes backwards. This model trusts
     * the client to pass the context it read, as the tests do.)
     */
    fun put(value: String, context: VectorClock, node: String): Version {
        val written = Version(value, context.increment(node))
        versions = prune(versions + written)
        return written
    }

    /** Replication or read repair: versions from another replica arrive, and the same pruning applies. Given. */
    fun receive(incoming: List<Version>) {
        versions = prune(versions + incoming)
    }

    /** The context a client passes back after reading every sibling: the merge of their clocks. Given. */
    fun context(): VectorClock = versions.fold(VectorClock()) { acc, v -> acc.merge(v.clock) }

    /** Keeps each version unless another one descends from it (is AFTER it), and drops duplicates. Given. */
    private fun prune(candidates: List<Version>): List<Version> =
        candidates.distinctBy { it.clock }.filter { v -> candidates.none { it.clock.compare(v.clock) == Order.AFTER } }
}
