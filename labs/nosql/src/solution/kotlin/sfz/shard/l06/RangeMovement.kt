package sfz.shard.l06

import java.util.TreeMap

/**
 * A token range `(start, end]`: every token after [start], up to and including [end]. The range that
 * ends at the smallest token starts at the largest one and wraps past the top of the ring.
 */
data class TokenRange(val start: Long, val end: Long) {
    /** True when [token] falls in this range. Given. */
    operator fun contains(token: Long): Boolean =
        if (start < end) token > start && token <= end else token > start || token <= end

    /** How many tokens the range covers, as a fraction of the 2^64 tokens on the ring. Given. */
    val share: Double get() = if (start == end) 1.0 else (end - start).toULong().toDouble() / RING_SIZE

    override fun toString() = "($start,$end]"

    companion object {
        const val RING_SIZE = 18446744073709551616.0
    }
}

/**
 * One datacenter and one rack with replication factor [rf], the shape of the lab cluster. The
 * replicas of a range are the first [rf] distinct nodes walking clockwise from the token that ends
 * it, as in lesson 2 (and as NetworkTopologyStrategy does when there is only one rack). Everything
 * in this class is given.
 */
class Ring(val tokens: Map<Long, String>, val rf: Int) {
    private val ring = TreeMap(tokens)

    /** The nodes on the ring. */
    val nodes: Set<String> get() = ring.values.toSortedSet()

    /** The ranges between consecutive tokens, each ending at a token, in ring order. */
    val ranges: List<TokenRange> = ring.keys.toList().let { t -> t.indices.map { i -> TokenRange(t[(i + t.size - 1) % t.size], t[i]) } }

    /** The replicas of whatever range [token] is in: walk clockwise from the first token at or after it. */
    fun replicasOf(token: Long): List<String> =
        (ring.tailMap(token, true).values.asSequence() + ring.headMap(token, false).values.asSequence())
            .distinct().take(rf).toList()

    /** The replicas of one range of this ring, primary first. */
    fun replicas(range: TokenRange): List<String> = replicasOf(range.end)

    /** Every range of this ring that [node] holds a copy of. */
    fun rangesOf(node: String): Set<TokenRange> = ranges.filter { node in replicas(it) }.toSet()

    /** The share of all the data that [node] holds a copy of: `Owns (effective)` in `nodetool status <keyspace>`. */
    fun owns(node: String): Double = rangesOf(node).sumOf { it.share }

    /** The same ring with [node] added at [newTokens]. */
    fun withNode(node: String, newTokens: Collection<Long>): Ring = Ring(tokens + newTokens.associateWith { node }, rf)

    /** The same ring with every token of [node] taken off. */
    fun withoutNode(node: String): Ring = Ring(tokens.filterValues { it != node }, rf)
}

/**
 * What moves when the ring changes. Every answer is a map from a node to a set of ranges, and the
 * ranges are always ranges of the ring that has MORE tokens (the ring after a join, or before a
 * decommission), because those are the pieces that move as a whole.
 *
 * Your job: [bootstrapSources], [cleanup] and [decommissionTargets].
 */
object RangeMovement {
    /**
     * A node joins: [after] is [before] plus [joining]'s tokens. For every range of [after] that
     * [joining] now replicates, find the node it streams that range from. Cassandra (with its default
     * `cassandra.consistent.rangemovement=true`) streams each range from the replica the newcomer
     * REPLACES: the node that held the range before and doesn't after. If no node drops out (the
     * cluster had fewer nodes than [Ring.rf]), use the first replica it had before.
     * Returns source node -> the ranges [joining] streams from it.
     */
    fun bootstrapSources(before: Ring, after: Ring, joining: String): Map<String, Set<TokenRange>> {
        val plan = sortedMapOf<String, MutableSet<TokenRange>>()
        for (range in after.rangesOf(joining)) {
            // the range is a piece of one range of the old ring, so it had that range's replicas
            val old = before.replicasOf(range.end)
            val new = after.replicas(range)
            val source = (old - new.toSet()).singleOrNull() ?: old.first()
            plan.getOrPut(source) { linkedSetOf() } += range
        }
        return plan
    }

    /**
     * After a join, each old node still has the data for ranges it no longer replicates: Cassandra
     * doesn't delete it by itself. `nodetool cleanup` on that node deletes exactly those ranges.
     * Returns node -> the ranges of [after] it held a copy of in [before] but doesn't replicate in
     * [after]. Leave out nodes with nothing to clean.
     */
    fun cleanup(before: Ring, after: Ring): Map<String, Set<TokenRange>> {
        val plan = sortedMapOf<String, MutableSet<TokenRange>>()
        for (range in after.ranges) {
            val old = before.replicasOf(range.end)
            val new = after.replicas(range).toSet()
            for (node in old) if (node !in new) plan.getOrPut(node) { linkedSetOf() } += range
        }
        return plan
    }

    /**
     * `nodetool decommission` on [leaving]: before it goes, it streams every range it replicates to
     * the node that becomes a replica of that range once it is gone (the one that wasn't a replica
     * before). Returns receiving node -> the ranges of [ring] it receives.
     */
    fun decommissionTargets(ring: Ring, leaving: String): Map<String, Set<TokenRange>> {
        val without = ring.withoutNode(leaving)
        val plan = sortedMapOf<String, MutableSet<TokenRange>>()
        for (range in ring.rangesOf(leaving)) {
            val old = ring.replicas(range).toSet()
            val new = without.replicasOf(range.end) // the bigger range of the smaller ring that contains this one
            for (node in new) if (node !in old) plan.getOrPut(node) { linkedSetOf() } += range
        }
        return plan
    }
}
