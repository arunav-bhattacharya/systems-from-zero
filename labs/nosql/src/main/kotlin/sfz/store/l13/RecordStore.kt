package sfz.store.l13

import java.nio.ByteBuffer
import kotlin.math.ceil
import kotlin.math.ln
import kotlin.math.max

/** Neo4j's page size: the page cache moves store files in and out of memory 8 KB at a time. */
const val PAGE_SIZE = 8192

/** Record sizes of Neo4j's record formats (`standard` and `aligned`), from NodeRecordFormat and RelationshipRecordFormat. */
const val NODE_RECORD_SIZE = 15
const val REL_RECORD_SIZE = 34

/** "No record": the end of a chain, or a node with no relationships. Stored as `ff ff ff ff`. */
const val NONE = -1L

/** Where record [id] sits in an `aligned` store file. */
data class Location(val page: Long, val offsetInPage: Int, val fileOffset: Long)

/**
 * Given. In the `aligned` format a record never spans two pages: each page holds `PAGE_SIZE / recordSize`
 * whole records and the leftover bytes at its end are padding. Node 2 is at byte 30; relationship 28 at byte 952.
 */
fun locate(id: Long, recordSize: Int): Location {
    val perPage = PAGE_SIZE / recordSize
    val page = id / perPage
    val offset = ((id % perPage) * recordSize).toInt()
    return Location(page, offset, page * PAGE_SIZE + offset)
}

/**
 * The size of an `aligned` store file that holds [records] records: whole pages only, at least one page.
 * Neo4j wrote 73,728 bytes (9 pages) for 2,037 relationships, and 8,192 bytes for 28 nodes.
 */
fun alignedStoreBytes(records: Long, recordSize: Int): Long {
    TODO("whole pages: PAGE_SIZE / recordSize records per page, rounded up, at least one page")
}

/** A decoded node record: 15 bytes on disk. */
data class NodeRecord(
    val id: Long,
    val inUse: Boolean,
    val nextRel: Long,   // the first relationship of this node's chain (the newest), or NONE
    val nextProp: Long,  // the first property record, or NONE (this lab never stores properties)
    val label: Int,      // one label id, kept inline in the 5-byte label field
    val dense: Boolean,  // true once the node has so many relationships that Neo4j groups them by type
)

/**
 * A decoded relationship record: 34 bytes on disk. Every relationship sits in TWO chains, one per end node,
 * so it carries a prev and a next pointer for each. The head of a chain has no prev, and Neo4j uses that
 * field to store the chain's length instead: the node's degree.
 */
data class RelRecord(
    val id: Long,
    val inUse: Boolean,
    val firstNode: Long,            // the start node (the arrow's tail)
    val secondNode: Long,           // the end node (the arrow's head)
    val type: Int,                  // relationship type id: USES = 0, TRANSFERRED_TO = 1 in the fraud graph
    val firstPrev: Long,            // previous relationship in firstNode's chain, or firstNode's degree if this is its head
    val firstNext: Long,            // next relationship in firstNode's chain, or NONE
    val secondPrev: Long,           // the same two pointers for secondNode's chain
    val secondNext: Long,
    val nextProp: Long,             // first property record, or NONE
    val firstInFirstChain: Boolean, // this record is the head of firstNode's chain
    val firstInSecondChain: Boolean,// this record is the head of secondNode's chain
)

/**
 * A tiny model of Neo4j's record store: a node file and a relationship file of fixed-size records, in the same
 * byte layout Neo4j's `aligned` format uses for ids below 2^31 (big-endian ints, -1 as `ff ff ff ff`).
 * Finding record N never searches anything: it's arithmetic on N. Every [readNode] and [readRel] counts one
 * record read in [recordReads], which is how the tests measure what a walk costs.
 */
class RecordStore(maxNodes: Int = 100_000, maxRelationships: Int = 400_000) {
    private val nodeFile: ByteBuffer = ByteBuffer.allocate(maxNodes * NODE_RECORD_SIZE)
    private val relFile: ByteBuffer = ByteBuffer.allocate(maxRelationships * REL_RECORD_SIZE)

    var nodeCount = 0L
        private set
    var relationshipCount = 0L
        private set

    /** Record reads since the last [resetCounters]. */
    var recordReads = 0L
        private set

    fun resetCounters() { recordReads = 0 }

    // ---- given: encoding and decoding, one record at an offset computed from its id ----

    fun readNode(id: Long): NodeRecord {
        recordReads++
        val at = (id * NODE_RECORD_SIZE).toInt()
        val header = nodeFile.get(at).toInt()
        val nextRel = nodeFile.getInt(at + 1).toLong()
        val nextProp = nodeFile.getInt(at + 5).toLong()
        val labelLow = nodeFile.getInt(at + 9).toLong() and 0xFFFFFFFFL
        val labelHigh = nodeFile.get(at + 13).toLong() and 0xFF
        val labelField = (labelHigh shl 32) or labelLow
        val extra = nodeFile.get(at + 14).toInt()
        return NodeRecord(id, header and 1 == 1, nextRel, nextProp, (labelField and 0xFFFFFFFFFL).toInt(), extra and 1 == 1)
    }

    fun writeNode(r: NodeRecord) {
        val at = (r.id * NODE_RECORD_SIZE).toInt()
        // Neo4j's inline label field: the label count in bits 36-38, the label ids packed below it
        val labelField = (1L shl 36) or r.label.toLong()
        nodeFile.put(at, if (r.inUse) 1 else 0)
        nodeFile.putInt(at + 1, r.nextRel.toInt())
        nodeFile.putInt(at + 5, r.nextProp.toInt())
        nodeFile.putInt(at + 9, labelField.toInt())
        nodeFile.put(at + 13, (labelField ushr 32).toByte())
        nodeFile.put(at + 14, if (r.dense) 1 else 0)
    }

    fun readRel(id: Long): RelRecord {
        recordReads++
        val at = (id * REL_RECORD_SIZE).toInt()
        val markers = relFile.get(at + 33).toInt()
        return RelRecord(
            id = id,
            inUse = relFile.get(at).toInt() and 1 == 1,
            firstNode = relFile.getInt(at + 1).toLong(),
            secondNode = relFile.getInt(at + 5).toLong(),
            type = relFile.getInt(at + 9),
            firstPrev = relFile.getInt(at + 13).toLong(),
            firstNext = relFile.getInt(at + 17).toLong(),
            secondPrev = relFile.getInt(at + 21).toLong(),
            secondNext = relFile.getInt(at + 25).toLong(),
            nextProp = relFile.getInt(at + 29).toLong(),
            firstInFirstChain = markers and 1 != 0,
            firstInSecondChain = markers and 2 != 0,
        )
    }

    fun writeRel(r: RelRecord) {
        val at = (r.id * REL_RECORD_SIZE).toInt()
        relFile.put(at, if (r.inUse) 1 else 0)
        relFile.putInt(at + 1, r.firstNode.toInt())
        relFile.putInt(at + 5, r.secondNode.toInt())
        relFile.putInt(at + 9, r.type)
        relFile.putInt(at + 13, r.firstPrev.toInt())
        relFile.putInt(at + 17, r.firstNext.toInt())
        relFile.putInt(at + 21, r.secondPrev.toInt())
        relFile.putInt(at + 25, r.secondNext.toInt())
        relFile.putInt(at + 29, r.nextProp.toInt())
        relFile.put(at + 33, ((if (r.firstInFirstChain) 1 else 0) or (if (r.firstInSecondChain) 2 else 0)).toByte())
    }

    /** The raw bytes of a record, as `od -t x1` would show them in the store file. */
    fun nodeBytes(id: Long): ByteArray = ByteArray(NODE_RECORD_SIZE).also { nodeFile.get((id * NODE_RECORD_SIZE).toInt(), it) }
    fun relBytes(id: Long): ByteArray = ByteArray(REL_RECORD_SIZE).also { relFile.get((id * REL_RECORD_SIZE).toInt(), it) }

    /** Given: a new node with one label and no relationships. Ids are handed out 0, 1, 2, ... like Neo4j's. */
    fun createNode(label: Int): Long {
        val id = nodeCount++
        writeNode(NodeRecord(id, inUse = true, nextRel = NONE, nextProp = NONE, label = label, dense = false))
        return id
    }

    // ---- the exercises ----

    /**
     * Creates the relationship `from -[type]-> to` and links it in at the HEAD of both nodes' chains, as Neo4j
     * does. For each end node, in the order from, then to:
     *
     * - read the node; its `nextRel` is the old head (or NONE);
     * - if there's an old head, read it: its prev field for this node holds the degree d; the new record gets
     *   prev = d + 1 and next = old head; then rewrite the old head with prev = the new id and its
     *   first-in-chain flag for this node cleared (re-read it first: it may be the same record for both ends);
     * - if there's none, the new record gets prev = 1 (the degree) and next = NONE;
     * - the new record is first in this node's chain, and the node's `nextRel` becomes the new id.
     *
     * Which pointers are "this node's" in an old head? The first pair if `old.firstNode == node`, else the second.
     * `from != to` (self-loops aren't needed here). nextProp stays NONE. Returns the new relationship's id.
     */
    fun createRelationship(from: Long, to: Long, type: Int): Long {
        TODO("link the new record in at the head of from's chain, then to's, as the KDoc says")
    }

    /**
     * [node]'s relationship records, newest first, by walking its chain: read the node, then read each
     * relationship and follow `firstNext` if the node is its first node, `secondNext` otherwise, until NONE.
     * One record read for the node plus one per relationship. No search anywhere.
     */
    fun relationshipsOf(node: Long): List<RelRecord> {
        TODO("start at the node's nextRel and follow firstNext or secondNext until NONE")
    }

    /** How many relationships [node] has, in at most two record reads: the head of the chain stores it. */
    fun degree(node: Long): Long {
        TODO("read the node, then the head of its chain: its prev field for this node is the degree")
    }

    /**
     * A breadth-first walk from [start], following relationships in either direction (only those of [type],
     * if given), up to [hops] hops. Returns every node reached, except [start], with the fewest hops to it.
     * Walk each frontier node's chain with [relationshipsOf]; the node at the other end of a record is
     * `secondNode` if the frontier node is its `firstNode`, and `firstNode` otherwise.
     */
    fun expand(start: Long, hops: Int, type: Int? = null): Map<Long, Int> {
        TODO("breadth first: walk each frontier node's chain, keep the first hop count for every new node")
    }
}

/**
 * Given: the same graph stored the relational way, as rows of a link table `rel(from, to, type)` with a B+tree
 * index on `from` and one on `to` (lesson 4 of this track, B+trees). Finding a node's relationships is
 * two index lookups, and each lookup descends the tree: [height] page reads, counted in [pageReads].
 */
class JoinTableGraph(private val fanout: Int = 200) {
    private data class Row(val id: Long, val from: Long, val to: Long, val type: Int)
    private val byFrom = HashMap<Long, MutableList<Row>>()
    private val byTo = HashMap<Long, MutableList<Row>>()
    private var rows = 0L

    var pageReads = 0L
        private set

    fun resetCounters() { pageReads = 0 }

    /** Levels of a B+tree over all rows: about log base [fanout] of the row count, at least 1. */
    val height: Int get() = max(1, ceil(ln(max(rows, 2).toDouble()) / ln(fanout.toDouble())).toInt())

    fun addRelationship(from: Long, to: Long, type: Int): Long {
        val row = Row(rows++, from, to, type)
        byFrom.getOrPut(from) { mutableListOf() } += row
        byTo.getOrPut(to) { mutableListOf() } += row
        return row.id
    }

    /** (relationship id, other node, type) for every row that touches [node]: one lookup in each index. */
    fun relationshipsOf(node: Long): List<Triple<Long, Long, Int>> {
        pageReads += 2L * height
        val out = byFrom[node].orEmpty().map { Triple(it.id, it.to, it.type) } + byTo[node].orEmpty().map { Triple(it.id, it.from, it.type) }
        return out.sortedByDescending { it.first }
    }

    /** The same breadth-first walk as [RecordStore.expand]. */
    fun expand(start: Long, hops: Int, type: Int? = null): Map<Long, Int> {
        val reached = linkedMapOf<Long, Int>()
        val seen = hashSetOf(start)
        var frontier = listOf(start)
        for (hop in 1..hops) {
            val next = mutableListOf<Long>()
            for (node in frontier) for ((_, other, t) in relationshipsOf(node)) {
                if (type != null && t != type) continue
                if (seen.add(other)) { reached[other] = hop; next += other }
            }
            frontier = next
        }
        return reached
    }
}
