package sfz.nosql.l06

/** One version of a value. The coordinator stamps every write; a higher [timestamp] is newer. */
data class Versioned(val value: String, val timestamp: Long)

/** One machine that holds a copy. A replica that is down neither stores nor answers. */
class Replica(val name: String) {
    var up: Boolean = true
    val data: MutableMap<String, Versioned> = HashMap()
}

/** What a write did. */
sealed interface WriteResult {
    /** At least W replicas stored the version and acknowledged it. */
    data class Ok(val acks: Int) : WriteResult

    /** Fewer than W replicas stored it in time. The ones that did KEEP it: there is no rollback. */
    data class TimedOut(val acks: Int) : WriteResult

    /** Fewer than W replicas were up, so the coordinator didn't even try. Nothing was stored. */
    data object Unavailable : WriteResult
}

/** What a read did. */
sealed interface ReadResult {
    /** [value] is the newest version among the replicas asked (null if none had the key). [repaired] got it written back. */
    data class Ok(val value: Versioned?, val repaired: List<String>) : ReadResult

    /** Fewer than R replicas were up. */
    data object Unavailable : ReadResult
}

/**
 * A leaderless store with N copies of every key, Dynamo and Cassandra style. Every request names
 * its own W or R, the way a Cassandra client picks a consistency level per statement.
 *
 * Replicas are named A, B, C, ... The coordinator sends every write to every replica; the
 * `reaches` argument says which messages actually arrive (the others are lost, as on a bad
 * network). Reads ask R replicas and keep the newest version: last write wins, by timestamp.
 *
 * Your job: [write], [read] and [staleReadPossible]. Everything else is given.
 */
class QuorumStore(val n: Int) {
    init {
        require(n in 1..26) { "1 to 26 replicas" }
    }

    /** The replicas, A, B, C, ... Given. */
    val replicas: List<Replica> = (0 until n).map { Replica(('A' + it).toString()) }

    /** Their names, in order. Given. */
    val names: List<String> get() = replicas.map { it.name }

    /** The coordinator's clock: every write gets the next tick. */
    private var clock = 0L

    fun replica(name: String): Replica = replicas.first { it.name == name }

    /** Crash a replica: it keeps its data but stores and answers nothing until [recover]. Given. */
    fun fail(name: String) {
        replica(name).up = false
    }

    /** Bring a replica back, with whatever data it had when it failed. Given. */
    fun recover(name: String) {
        replica(name).up = true
    }

    /** What one replica holds for [key], up or down. Given. */
    fun valueAt(name: String, key: String): Versioned? = replica(name).data[key]

    /**
     * Writes [value] for [key] and waits for [w] acknowledgements.
     *
     * 1. If fewer than [w] replicas are up: [WriteResult.Unavailable], and store nothing.
     * 2. Stamp a new version with the next clock tick (`++clock`).
     * 3. Every replica that is up AND in [reaches] stores it (unless it already holds a newer
     *    version: last write wins) and counts as one ack.
     * 4. acks >= w: [WriteResult.Ok]. Otherwise [WriteResult.TimedOut]; do NOT undo the stores.
     */
    fun write(key: String, value: String, w: Int, reaches: Collection<String> = names): WriteResult {
        // like Cassandra's Unavailable: the coordinator knows too few replicas are alive
        if (replicas.count { it.up } < w) return WriteResult.Unavailable
        val version = Versioned(value, ++clock)
        var acks = 0
        for (rep in replicas) {
            if (!rep.up || rep.name !in reaches) continue // down, or the message was lost
            storeIfNewer(rep, key, version)
            acks++
        }
        // too few acks is a timeout, not a rollback: the copies that landed stay
        return if (acks >= w) WriteResult.Ok(acks) else WriteResult.TimedOut(acks)
    }

    /**
     * Reads [key] from [r] replicas: the first [r] replicas in [order] that are up.
     *
     * 1. If fewer than [r] replicas in [order] are up: [ReadResult.Unavailable].
     * 2. The answer is the version with the highest timestamp among those r (null if none has it).
     * 3. Read repair: every one of those r replicas whose version is older, or missing, stores the
     *    answer. List their names in [ReadResult.Ok.repaired], in the order you asked them.
     *    Replicas you didn't ask are left alone.
     */
    fun read(key: String, r: Int, order: List<String> = names): ReadResult {
        val asked = order.map(::replica).filter { it.up }.take(r)
        if (asked.size < r) return ReadResult.Unavailable
        // last write wins: the newest timestamp among the answers
        val newest = asked.mapNotNull { it.data[key] }.maxByOrNull { it.timestamp }
            ?: return ReadResult.Ok(null, emptyList())
        // the coordinator now knows who is behind, and fixes them on the way out
        val stale = asked.filter { (it.data[key]?.timestamp ?: Long.MIN_VALUE) < newest.timestamp }
        stale.forEach { storeIfNewer(it, key, newest) }
        return ReadResult.Ok(newest, stale.map { it.name })
    }

    private fun storeIfNewer(rep: Replica, key: String, version: Versioned) {
        val old = rep.data[key]
        if (old == null || old.timestamp < version.timestamp) rep.data[key] = version
    }

    companion object {
        /**
         * Out of [n] replicas, can a read of [r] of them miss a write that [w] of them stored?
         *
         * Decide by brute force, not by formula: try every set of [w] replicas that could hold the
         * write and every set of [r] replicas a read could ask. Return true if some pair of sets
         * has no replica in common.
         */
        fun staleReadPossible(n: Int, r: Int, w: Int): Boolean {
            val all = (0 until n).toList()
            val writeSets = subsets(all, w)
            val readSets = subsets(all, r)
            // one disjoint pair is enough: that read sees none of the copies
            return writeSets.any { ws -> readSets.any { rs -> rs.none { it in ws } } }
        }

        /** Every subset of [items] with exactly [k] elements. Given. */
        fun <T> subsets(items: List<T>, k: Int): List<Set<T>> {
            if (k == 0) return listOf(emptySet())
            if (items.size < k) return emptyList()
            val first = items.first()
            val rest = items.drop(1)
            return subsets(rest, k - 1).map { it + first } + subsets(rest, k)
        }
    }
}
