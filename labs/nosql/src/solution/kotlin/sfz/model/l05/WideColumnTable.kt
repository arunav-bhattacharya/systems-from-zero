package sfz.model.l05

import java.util.TreeMap

/**
 * A CQL primary key: `PRIMARY KEY ((partitionKey...), clustering...)`.
 * Inside a partition, rows sort by the clustering columns, left to right, as strings, ascending.
 */
data class PrimaryKey(val partitionKey: List<String>, val clustering: List<String>)

/**
 * One version of one row, as the memtable or an SSTable holds it. [values] is the whole row
 * (key columns included), or null for a tombstone. All times are seconds on one shared clock.
 *
 * Real Cassandra keeps a timestamp on every cell (every column of every row); this model keeps
 * one per row, which is enough to see the write path, tombstones and compaction.
 */
data class Version(val values: Map<String, String>?, val timestamp: Long, val expiresAt: Long? = null) {
    val isTombstone: Boolean get() = values == null

    /** A row a read may return: not a tombstone, and not past its TTL. */
    fun isLive(now: Long): Boolean = values != null && (expiresAt == null || now < expiresAt)

    /** When this version stopped being live (the delete, or the TTL expiry), or null if it's still live. */
    fun deadSince(now: Long): Long? = when {
        values == null -> timestamp
        expiresAt != null && now >= expiresAt -> expiresAt
        else -> null
    }
}

/** One flushed memtable: immutable, sorted, never changed in place. Partition key values -> clustering values -> version. */
class SSTable(val partitions: Map<List<String>, Map<List<String>, Version>>)

/** A range on one column: `column >= from AND column < until` (either end may be open). */
data class Range(val column: String, val from: String? = null, val until: String? = null) {
    fun contains(value: String?): Boolean =
        value != null && (from == null || value >= from) && (until == null || value < until)
}

/** A CQL SELECT: equalities, at most one range, a LIMIT, and whether it says ALLOW FILTERING. */
data class Select(
    val where: Map<String, String> = emptyMap(),
    val range: Range? = null,
    val limit: Int = Int.MAX_VALUE,
    val allowFiltering: Boolean = false,
)

/** The rows a read returned, and what it had to look at to find them. */
data class ReadResult(
    val rows: List<Map<String, String>>,
    val partitionsRead: Int,
    val liveRowsRead: Int,
    val tombstonesRead: Int,
)

/** Cassandra's answer to a query the table's key can't serve. */
class InvalidQueryException(message: String) : RuntimeException(message)

/** A read that met more tombstones than `tombstone_failure_threshold` and gave up. */
class TombstoneOverwhelmingException(val tombstones: Int) :
    RuntimeException("Scanned over $tombstones tombstones during query; query aborted")

/**
 * One Cassandra table on one replica: a memtable, a list of SSTables, and reads that merge them.
 *
 * Writes never change anything in place. [insert] and [delete] add a timestamped [Version] to the
 * memtable; [flush] turns the memtable into a new immutable [SSTable]. A read merges every copy of a
 * row it finds and keeps the newest. [compact] rewrites all SSTables into one.
 *
 * Your job: [filteringReason], [mergedPartition], [select] and [compact]. Everything else is given.
 */
class WideColumnTable(val key: PrimaryKey, val tombstoneFailureThreshold: Int = 100_000) {
    /** Where every write lands first: partition -> clustering -> the newest version written so far. */
    val memtable: MutableMap<List<String>, TreeMap<List<String>, Version>> = HashMap()

    /** Flushed memtables, oldest first. */
    val sstables: MutableList<SSTable> = mutableListOf()

    private fun partitionOf(row: Map<String, String>) = key.partitionKey.map { requireNotNull(row[it]) { "missing $it" } }
    private fun clusteringOf(row: Map<String, String>) = key.clustering.map { requireNotNull(row[it]) { "missing $it" } }

    /** Writes [version] into the memtable unless the memtable already holds something newer. Given. */
    private fun append(partition: List<String>, clustering: List<String>, version: Version) {
        val rows = memtable.getOrPut(partition) { TreeMap(CLUSTERING_ORDER) }
        val old = rows[clustering]
        if (old == null || newer(version, old)) rows[clustering] = version
    }

    /** INSERT (or UPDATE: in Cassandra they are the same thing) of a whole row. Given. */
    fun insert(row: Map<String, String>, timestamp: Long, ttlSeconds: Long? = null) {
        append(partitionOf(row), clusteringOf(row), Version(row, timestamp, ttlSeconds?.let { timestamp + it }))
    }

    /** DELETE of one row, named by its full primary key: writes a tombstone. Given. */
    fun delete(keyValues: Map<String, String>, timestamp: Long) {
        append(partitionOf(keyValues), clusteringOf(keyValues), Version(null, timestamp))
    }

    /** nodetool flush: the memtable becomes a new SSTable, and a new empty memtable starts. Given. */
    fun flush() {
        if (memtable.isEmpty()) return
        sstables += SSTable(memtable.mapValues { (_, rows) -> TreeMap(rows) })
        memtable.clear()
    }

    /**
     * Anti-entropy repair, simplified: every version [other] holds that is newer than what this
     * replica holds (or that this replica doesn't hold at all) is written into this memtable. Given.
     */
    fun repairFrom(other: WideColumnTable) {
        val partitions = other.memtable.keys + other.sstables.flatMap { it.partitions.keys }
        for (p in partitions) {
            val mine = mergedPartition(p)
            for ((c, v) in other.mergedPartition(p)) {
                val have = mine[c]
                if (have == null || newer(v, have)) append(p, c, v)
            }
        }
    }

    /**
     * Why Cassandra would refuse [q] without ALLOW FILTERING, or null if [q] is a slice of one partition.
     *
     * 1. A partition key column without `=` in `where`: [ALLOW_FILTERING]. (Without the whole
     *    partition key there is no token, so no way to know which partition to read.)
     * 2. Count the leading clustering columns that have `=`: call it `fixed`.
     * 3. Any OTHER clustering column restricted (by `=` in `where`, or by the range) when it isn't
     *    `clustering[fixed]` itself: [gap] of that column and `clustering[fixed]`. A range on
     *    `clustering[fixed]` is fine: that's the slice.
     * 4. A regular (non-key) column in `where` or in the range: [ALLOW_FILTERING].
     * 5. Otherwise null.
     */
    fun filteringReason(q: Select): String? {
        // 1. no partition key, no token: the store can't know which partition holds the answer
        if (!q.where.keys.containsAll(key.partitionKey)) return ALLOW_FILTERING
        // 2. the clustering prefix fixed by =
        var fixed = 0
        while (fixed < key.clustering.size && key.clustering[fixed] in q.where) fixed++
        // 3. a restriction further right than the prefix (or the one range right after it) is a gap
        val restricted = q.where.keys + listOfNotNull(q.range?.column)
        for ((i, column) in key.clustering.withIndex()) {
            if (i < fixed || column !in restricted) continue
            val isTheSliceRange = i == fixed && q.range?.column == column && column !in q.where
            if (!isTheSliceRange) return gap(column, key.clustering[fixed])
        }
        // 4. a column that isn't in the key at all can only be checked by reading rows
        val keyColumns = key.partitionKey + key.clustering
        if (restricted.any { it !in keyColumns }) return ALLOW_FILTERING
        return null
    }

    /**
     * Every row of [partition] as a read sees it: for each clustering key, the newest version
     * found in the memtable or any SSTable ([newer] decides). Tombstones and expired rows stay in
     * the result: a read has to step over them, and [select] counts them.
     */
    fun mergedPartition(partition: List<String>): TreeMap<List<String>, Version> {
        val merged = TreeMap<List<String>, Version>(CLUSTERING_ORDER)
        // every place a copy of this partition can be: each SSTable, then the memtable
        val sources = sstables.mapNotNull { it.partitions[partition] } + listOfNotNull(memtable[partition])
        for (rows in sources) {
            for ((clustering, version) in rows) {
                val old = merged[clustering]
                if (old == null || newer(version, old)) merged[clustering] = version
            }
        }
        return merged
    }

    /**
     * Runs [q] at time [now].
     *
     * 1. [filteringReason]: if there is one and `q.allowFiltering` is false, throw
     *    [InvalidQueryException] with that reason.
     * 2. The partitions to read: just the one named by `where` when the whole partition key is
     *    there; otherwise every partition this replica holds, in [partitionOrder].
     * 3. Walk each [mergedPartition] in clustering order. When `q` is a slice (no reason), the
     *    store seeks straight to the slice, so rows outside it are neither read nor counted; when
     *    filtering, every row of the partition is read.
     * 4. For each row read: not live -> count a tombstone (an expired TTL row counts as one), and
     *    throw [TombstoneOverwhelmingException] once the count passes [tombstoneFailureThreshold].
     *    Live -> count it in liveRowsRead, and return it if it matches every `where` value and the range.
     * 5. Stop as soon as `q.limit` rows are returned.
     */
    fun select(q: Select, now: Long): ReadResult {
        val reason = filteringReason(q)
        if (reason != null && !q.allowFiltering) throw InvalidQueryException(reason)

        val partitions = if (q.where.keys.containsAll(key.partitionKey)) {
            listOf(key.partitionKey.map { q.where.getValue(it) })
        } else {
            partitionOrder()
        }

        val rows = mutableListOf<Map<String, String>>()
        var partitionsRead = 0
        var live = 0
        var tombstones = 0
        for (p in partitions) {
            val merged = mergedPartition(p)
            if (merged.isEmpty()) continue
            partitionsRead++
            for ((clustering, version) in merged) {
                // a slice reads only its own rows; a filtering query reads them all
                if (reason == null && !inSlice(clustering, q)) continue
                if (!version.isLive(now)) {
                    tombstones++
                    if (tombstones > tombstoneFailureThreshold) throw TombstoneOverwhelmingException(tombstones)
                    continue
                }
                live++
                val row = version.values!!
                val matches = q.where.all { (c, v) -> row[c] == v } && (q.range == null || q.range.contains(row[q.range.column]))
                if (matches) {
                    rows += row
                    if (rows.size >= q.limit) return ReadResult(rows, partitionsRead, live, tombstones)
                }
            }
        }
        return ReadResult(rows, partitionsRead, live, tombstones)
    }

    /**
     * Compaction: merge every SSTable into ONE new SSTable, then replace the list with it (or with
     * nothing, if nothing is left). The memtable is not touched: flush first.
     *
     * For each row keep only the newest version. Drop the row entirely when that newest version is
     * dead (a tombstone, or an expired TTL row) and has been dead for at least [gcGraceSeconds]:
     * `deadSince(now) + gcGraceSeconds <= now`. Anything dead for less than that stays, as a
     * tombstone, so that repair can still carry the delete to replicas that missed it.
     */
    fun compact(now: Long, gcGraceSeconds: Long) {
        val partitions = sstables.flatMap { it.partitions.keys }.toSet()
        val out = HashMap<List<String>, Map<List<String>, Version>>()
        for (p in partitions) {
            val merged = TreeMap<List<String>, Version>(CLUSTERING_ORDER)
            for (sstable in sstables) {
                for ((c, v) in sstable.partitions[p].orEmpty()) {
                    val old = merged[c]
                    if (old == null || newer(v, old)) merged[c] = v
                }
            }
            // purge only what has been dead for longer than gc_grace
            merged.entries.removeIf { (_, v) -> v.deadSince(now)?.let { it + gcGraceSeconds <= now } == true }
            if (merged.isNotEmpty()) out[p] = merged
        }
        sstables.clear()
        if (out.isNotEmpty()) sstables += SSTable(out)
    }

    /** Is [clustering] inside the slice [q] asks for: the `=` prefix, then the range on the next column? Given. */
    private fun inSlice(clustering: List<String>, q: Select): Boolean {
        for ((i, column) in key.clustering.withIndex()) {
            val wanted = q.where[column]
            if (wanted != null) {
                if (clustering[i] != wanted) return false
            } else {
                return q.range == null || q.range.column != column || q.range.contains(clustering[i])
            }
        }
        return true
    }

    /** Every partition this replica holds, in key order. (Cassandra walks them in token order.) Given. */
    fun partitionOrder(): List<List<String>> =
        (memtable.keys + sstables.flatMap { it.partitions.keys }).toSortedSet(CLUSTERING_ORDER).toList()

    /** How many SSTables this replica has on disk. Given. */
    val sstableCount: Int get() = sstables.size

    companion object {
        /** Cassandra's error for a query that would have to read and filter. */
        const val ALLOW_FILTERING = "Cannot execute this query as it might involve data filtering and thus may have " +
            "unpredictable performance. If you want to execute this query despite the performance unpredictability, use ALLOW FILTERING"

        /** Cassandra's error for skipping a clustering column. */
        fun gap(column: String, preceding: String) =
            "PRIMARY KEY column \"$column\" cannot be restricted as preceding column \"$preceding\" is not restricted"

        /** Compares clustering (or partition) values left to right, as strings. */
        val CLUSTERING_ORDER: Comparator<List<String>> = Comparator { a, b ->
            for (i in 0 until minOf(a.size, b.size)) {
                val c = a[i].compareTo(b[i])
                if (c != 0) return@Comparator c
            }
            a.size - b.size
        }

        /** Last write wins: the higher timestamp is newer; on a tie the tombstone wins, as in Cassandra. */
        fun newer(a: Version, than: Version): Boolean =
            a.timestamp > than.timestamp || (a.timestamp == than.timestamp && a.isTombstone && !than.isTombstone)
    }
}
