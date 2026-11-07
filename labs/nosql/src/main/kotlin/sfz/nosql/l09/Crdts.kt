package sfz.nosql.l09

// Your job in this file: LwwRegister.merge, GCounter.merge, and ORSet's remove, elements and merge.

/**
 * A last-write-wins register: the value whose write carries the higher wall-clock [timestamp]
 * wins, and on a tie the higher [node] name, so every replica picks the same winner. This is
 * Cassandra's rule for every cell. It always converges, and it silently drops the loser.
 */
data class LwwRegister(val value: String?, val timestamp: Long, val node: String) {
    /** The winner of this and [other]: higher timestamp, then higher node name. */
    fun merge(other: LwwRegister): LwwRegister {
        TODO("higher timestamp wins; on a tie, the higher node name")
    }
}

/**
 * A grow-only counter (G-Counter): one slot per replica, and a replica only ever adds to its own
 * slot. The value is the sum of the slots. Two copies merge by taking each slot's maximum, which
 * gives the same answer in any order, any number of times.
 */
data class GCounter(val slots: Map<String, Long> = emptyMap()) {
    /** [replica] counts [by] more (by >= 0). Given. */
    fun increment(replica: String, by: Long = 1): GCounter {
        require(by >= 0) { "a G-Counter only grows" }
        return GCounter(slots + (replica to (slots[replica] ?: 0) + by))
    }

    /** The count: the sum of every replica's slot. Given. */
    val value: Long get() = slots.values.sum()

    /** For each replica, the bigger of the two slots. */
    fun merge(other: GCounter): GCounter {
        TODO("for every replica in either counter, the bigger slot")
    }
}

/** A counter that goes up and down (PN-Counter): one G-Counter of increments, one of decrements. Given. */
data class PNCounter(val p: GCounter = GCounter(), val n: GCounter = GCounter()) {
    fun increment(replica: String, by: Long = 1) = copy(p = p.increment(replica, by))
    fun decrement(replica: String, by: Long = 1) = copy(n = n.increment(replica, by))
    val value: Long get() = p.value - n.value
    fun merge(other: PNCounter) = PNCounter(p.merge(other.p), n.merge(other.n))
}

/**
 * An observed-remove set (OR-Set). Every add carries a tag nobody else uses ("replica:counter").
 * A remove deletes the tags it has SEEN for that element, and nothing else. So an add that a
 * remove didn't see survives the merge: a concurrent add beats a concurrent remove.
 *
 * [adds] maps each element to the tags its adds created; [removed] holds every tag removed so far.
 */
data class ORSet(val adds: Map<String, Set<String>> = emptyMap(), val removed: Set<String> = emptySet()) {
    /** Adds [element] with a fresh [tag]. Given. */
    fun add(element: String, tag: String): ORSet = copy(adds = adds + (element to (adds[element].orEmpty() + tag)))

    /** Removes [element]: every tag this copy has seen for it goes into [removed]. */
    fun remove(element: String): ORSet {
        TODO("add every tag this copy has seen for element to removed")
    }

    /** The elements with at least one tag that hasn't been removed. */
    val elements: Set<String>
        get() {
            TODO("the elements that still have a tag not in removed")
        }

    /** The union of both: every tag either copy added, every tag either copy removed. */
    fun merge(other: ORSet): ORSet {
        TODO("union of the tags per element, union of the removed tags")
    }
}
