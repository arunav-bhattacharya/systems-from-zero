package sfz.shard.l09

/**
 * Given: OpenSearch's routing hash. Murmur3 (x86, 32-bit, seed 0) over the routing value's UTF-16 code units,
 * low byte first: the same function as OpenSearch's `Murmur3HashFunction.hash(String)`.
 */
fun routingHash(routing: String): Int {
    val bytes = ByteArray(routing.length * 2)
    routing.forEachIndexed { i, c ->
        bytes[2 * i] = c.code.toByte()
        bytes[2 * i + 1] = (c.code ushr 8).toByte()
    }
    return murmur3x86(bytes)
}

private fun murmur3x86(data: ByteArray): Int {
    val c1 = -0x3361d2af // 0xcc9e2d51
    val c2 = 0x1b873593
    var h = 0
    val blocks = data.size / 4
    for (i in 0 until blocks) {
        var k = (data[4 * i].toInt() and 0xff) or ((data[4 * i + 1].toInt() and 0xff) shl 8) or
            ((data[4 * i + 2].toInt() and 0xff) shl 16) or ((data[4 * i + 3].toInt() and 0xff) shl 24)
        k *= c1; k = Integer.rotateLeft(k, 15); k *= c2
        h = h xor k
        h = Integer.rotateLeft(h, 13); h = h * 5 + -0x19ab949c // 0xe6546b64
    }
    var k = 0
    val tail = blocks * 4
    when (data.size and 3) {
        3 -> { k = k xor ((data[tail + 2].toInt() and 0xff) shl 16); k = k xor ((data[tail + 1].toInt() and 0xff) shl 8); k = k xor (data[tail].toInt() and 0xff) }
        2 -> { k = k xor ((data[tail + 1].toInt() and 0xff) shl 8); k = k xor (data[tail].toInt() and 0xff) }
        1 -> k = k xor (data[tail].toInt() and 0xff)
    }
    if (data.size and 3 != 0) { k *= c1; k = Integer.rotateLeft(k, 15); k *= c2; h = h xor k }
    h = h xor data.size
    h = h xor (h ushr 16); h *= -0x7a143595 // 0x85ebca6b
    h = h xor (h ushr 13); h *= -0x3d4d51cb // 0xc2b2ae35
    return h xor (h ushr 16)
}

/**
 * Given: how many routing slots OpenSearch gives an index with [primaries] primary shards when you don't set
 * `index.number_of_routing_shards`: the largest `primaries x 2^k` up to 1,024, with k at least 1, so that
 * `_split` can later double the shards without moving documents between them. 3 primaries get 768 slots.
 */
fun routingNumShards(primaries: Int): Int {
    val log2Primaries = 32 - Integer.numberOfLeadingZeros(primaries - 1) // ceil(log2(primaries))
    val splits = maxOf(1, 10 - log2Primaries)
    return primaries shl splits
}

/**
 * The primary shard a document lives in. The docs write it `hash(_routing) % number_of_primary_shards`;
 * underneath, OpenSearch takes the hash modulo the routing slots and divides by the slots per shard:
 *
 *     floorMod(routingHash(routing), routingNumShards(primaries)) / (routingNumShards(primaries) / primaries)
 *
 * `_routing` is the document's `_id` unless you pass `?routing=`. M-0042 is in shard 2 of a 3-shard index.
 */
fun shardFor(routing: String, primaries: Int): Int {
    TODO("floorMod(routingHash(routing), slots) / (slots / primaries), with slots = routingNumShards(primaries)")
}

enum class Health { GREEN, YELLOW, RED }

/** One copy of one shard: the primary or a replica, on [node], or unassigned when [node] is null. */
class ShardCopy(val shard: Int, var primary: Boolean, var node: String?) {
    override fun toString() = "$shard${if (primary) "p" else "r"}@${node ?: "unassigned"}"
}

/**
 * A model of how a search cluster's elected cluster manager places shard copies, for one index.
 * [copies] is the routing table: every copy of every shard and where it lives.
 */
class SearchCluster(nodeNames: List<String>) {
    /** The nodes in the cluster, in the order they joined. */
    val nodes: MutableList<String> = nodeNames.toMutableList()
    val copies: MutableList<ShardCopy> = mutableListOf()

    var primaries = 0
        private set
    var replicas = 0
        private set

    fun copiesOn(node: String): List<ShardCopy> = copies.filter { it.node == node }
    fun copiesOf(shard: Int): List<ShardCopy> = copies.filter { it.shard == shard }
    fun primaryOf(shard: Int): ShardCopy = copies.first { it.shard == shard && it.primary }

    /**
     * Given: creates the index. Primary `s` goes to `nodes[s % nodes.size]`; then [allocate] places the replicas.
     */
    fun createIndex(primaries: Int, replicas: Int) {
        this.primaries = primaries
        this.replicas = replicas
        for (s in 0 until primaries) {
            copies += ShardCopy(s, primary = true, node = nodes[s % nodes.size])
            repeat(replicas) { copies += ShardCopy(s, primary = false, node = null) }
        }
        allocate()
    }

    /** Given: a node joins (or comes back empty) and the manager allocates what it can. Moving copies that are fine where they are, rebalancing, isn't modelled. */
    fun nodeJoined(node: String) {
        nodes += node
        allocate()
    }

    /**
     * Places every unassigned REPLICA whose primary is assigned, in shard order, then replica order. Two rules:
     *
     * - never on a node that already holds a copy of the same shard (a replica next to its primary protects nothing);
     * - among the nodes allowed, the one with the fewest copies; on a tie, the first one met when you scan
     *   [nodes] starting just after the primary's node and wrapping round.
     *
     * A replica with no allowed node stays unassigned. Never allocate a primary here: an unassigned primary
     * means every copy of that shard is gone, and OpenSearch won't make up an empty one.
     */
    fun allocate() {
        TODO("place each unassigned replica whose primary is assigned: not next to a copy of its shard, fewest copies, scan from after the primary")
    }

    /**
     * [node] leaves the cluster (it crashed, or you stopped it). For each copy it held, in shard order:
     *
     * - a replica becomes unassigned;
     * - a primary: if the shard has an assigned replica elsewhere, promote it (the first one in [copies]) and
     *   turn the lost copy into an unassigned replica; if not, the primary stays unassigned and the shard is lost.
     *
     * Then remove [node] from [nodes]. Don't allocate here: OpenSearch waits (`index.unassigned.node_left.delayed_timeout`,
     * one minute) in case the node comes back, and the caller calls [allocate] when the wait is over.
     */
    fun nodeLeft(node: String) {
        TODO("unassign the node's copies; promote a surviving replica for each lost primary; remove the node")
    }

    /** RED if any primary is unassigned, YELLOW if all primaries are assigned but a replica isn't, GREEN otherwise. */
    fun health(): Health {
        TODO("RED: a primary is unassigned; YELLOW: a replica is; GREEN: everything is assigned")
    }
}

/** One search result. [shard] is where it came from. */
data class Hit(val id: String, val score: Double, val shard: Int)

/**
 * An index split into shards by [shardFor], searched the way OpenSearch does it: query then fetch.
 * The counters say what one search cost.
 */
class ShardedIndex(val primaries: Int) {
    private val shards: List<MutableMap<String, String>> = List(primaries) { sortedMapOf() }

    /** Shard requests in the query phase of the last [search]: one per shard. */
    var shardRequests = 0
        private set
    /** (id, score) pairs the shards sent back to the coordinating node in the last [search]. */
    var hitsSentToCoordinator = 0
        private set
    /** Documents read in the fetch phase of the last [search]. */
    var documentsFetched = 0
        private set

    /** Given: stores the document in the shard its id routes to. */
    fun index(id: String, text: String) { shards[shardFor(id, primaries)][id] = text }

    fun docsIn(shard: Int): Int = shards[shard].size

    /** Given: the fetch phase reads one document's text from its shard. */
    fun fetch(hit: Hit): String { documentsFetched++; return shards[hit.shard].getValue(hit.id) }

    /**
     * Returns results `from` to `from + size` (best first; ties by id), the way a coordinating node does:
     *
     * 1. query phase: ask EVERY shard (count [shardRequests]) for its own best `from + size` hits, scored with
     *    [score] (a score of 0 or less means no match), and count every hit a shard sends back in [hitsSentToCoordinator];
     * 2. merge: sort all of them, best first, ties by id, and keep the page `from until from + size`;
     * 3. fetch phase: [fetch] the text of those hits only, and return them.
     *
     * Reset the three counters at the start.
     */
    fun search(score: (String) -> Double, from: Int = 0, size: Int = 10): List<Pair<Hit, String>> {
        TODO("query phase on every shard (top from + size each), merge, keep the page, then fetch only those")
    }
}
