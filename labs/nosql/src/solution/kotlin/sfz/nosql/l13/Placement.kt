package sfz.nosql.l13

import java.util.TreeMap

/** A Cassandra node as the snitch describes it: a name, a datacenter and a rack. */
data class Endpoint(val name: String, val dc: String, val rack: String)

/**
 * A token ring with vnodes: every token, sorted, and the endpoint that owns it. A key belongs to the
 * range that ends at the first token at or after the key's token, and its replicas come from walking
 * the ring clockwise from there.
 *
 * Your job: [networkTopology]. Everything else is given.
 */
class TokenRing(tokens: Map<Long, Endpoint>) {
    private val ring = TreeMap(tokens)

    init {
        require(ring.isNotEmpty()) { "a ring needs at least one token" }
    }

    /** Every endpoint on the ring. Given. */
    val endpoints: Set<Endpoint> get() = ring.values.toSet()

    /** The endpoints in the order the walk meets them, starting at the first token at or after [token], each token once. Given. */
    fun walk(token: Long): Sequence<Endpoint> =
        ring.tailMap(token, true).values.asSequence() + ring.headMap(token, false).values.asSequence()

    /** SimpleStrategy: the first [rf] distinct endpoints on the walk, whatever their datacenter or rack. Given. */
    fun simpleStrategy(token: Long, rf: Int): List<Endpoint> =
        walk(token).distinct().take(rf).toList()

    /**
     * NetworkTopologyStrategy, the way Cassandra 5.0 places replicas (`NetworkTopologyStrategy.calculateNaturalReplicas`).
     * [rf] gives each datacenter its own replication factor, such as `mapOf("dc1" to 3, "dc2" to 2)`.
     *
     * Walk the ring once from [token]. Keep separate books for each datacenter in [rf]:
     * - `wanted` = min(rf of the dc, number of endpoints in the dc);
     * - `rackRepeatsAllowed` = rf of the dc minus the number of racks in the dc (zero or less means none);
     * - the racks already used.
     *
     * For each endpoint the walk meets, in its own datacenter's books: skip it if the dc already has
     * `wanted` replicas or the endpoint is already a replica. If its rack is new, take it. If its rack
     * is already used, take it only while `rackRepeatsAllowed > 0` (and count one repeat off);
     * otherwise skip it. Stop when every datacenter has what it wants.
     *
     * Return the replicas in the order they were taken. That's the order `nodetool getendpoints` prints.
     */
    fun networkTopology(token: Long, rf: Map<String, Int>): List<Endpoint> {
        val byDc = endpoints.groupBy { it.dc }
        // one set of books per datacenter that has replicas and nodes
        class Books(val wanted: Int, var rackRepeatsAllowed: Int) {
            val racks = HashSet<String>()
            var taken = 0
        }
        val books = rf.filter { (dc, n) -> n > 0 && dc in byDc }.mapValues { (dc, n) ->
            val nodes = byDc.getValue(dc)
            Books(minOf(n, nodes.size), n - nodes.map { it.rack }.toSet().size)
        }
        val replicas = LinkedHashSet<Endpoint>()
        for (ep in walk(token)) {
            if (books.values.all { it.taken == it.wanted }) break
            val b = books[ep.dc] ?: continue          // a datacenter with no replicas here
            if (b.taken == b.wanted || ep in replicas) continue
            when {
                b.racks.add(ep.rack) -> Unit           // a rack we haven't used: always take it
                b.rackRepeatsAllowed > 0 -> b.rackRepeatsAllowed--  // fewer racks than copies: some rack must repeat
                else -> continue                       // keep looking for an unused rack
            }
            replicas += ep
            b.taken++
        }
        return replicas.toList()
    }

    companion object {
        /**
         * The token Cassandra's Murmur3Partitioner gives a text partition key: the first 64 bits of
         * MurmurHash3 x64 128 (seed 0) over the key's UTF-8 bytes. `murmur3("A-1001")` is
         * -4994511478997274402, the number `SELECT token(account_id)` prints. Given.
         */
        fun murmur3(key: String): Long {
            val data = key.toByteArray(Charsets.UTF_8)
            val length = data.size
            val c1 = -0x783c846eeebdac2bL // 0x87c37b91114253d5
            val c2 = 0x4cf5ad432745937fL
            var h1 = 0L
            var h2 = 0L
            fun block(i: Int): Long {
                var v = 0L
                for (b in 7 downTo 0) v = (v shl 8) or (data[i + b].toLong() and 0xff)
                return v
            }
            val blocks = length / 16
            for (i in 0 until blocks) {
                var k1 = block(i * 16)
                var k2 = block(i * 16 + 8)
                k1 *= c1; k1 = java.lang.Long.rotateLeft(k1, 31); k1 *= c2; h1 = h1 xor k1
                h1 = java.lang.Long.rotateLeft(h1, 27); h1 += h2; h1 = h1 * 5 + 0x52dce729
                k2 *= c2; k2 = java.lang.Long.rotateLeft(k2, 33); k2 *= c1; h2 = h2 xor k2
                h2 = java.lang.Long.rotateLeft(h2, 31); h2 += h1; h2 = h2 * 5 + 0x38495ab5
            }
            // the tail: Cassandra reads these bytes as SIGNED, which only matters for bytes >= 0x80
            val tail = blocks * 16
            var k1 = 0L
            var k2 = 0L
            val rest = length and 15
            for (i in rest - 1 downTo 8) k2 = k2 xor (data[tail + i].toLong() shl ((i - 8) * 8))
            if (rest > 8) { k2 *= c2; k2 = java.lang.Long.rotateLeft(k2, 33); k2 *= c1; h2 = h2 xor k2 }
            for (i in minOf(rest, 8) - 1 downTo 0) k1 = k1 xor (data[tail + i].toLong() shl (i * 8))
            if (rest > 0) { k1 *= c1; k1 = java.lang.Long.rotateLeft(k1, 31); k1 *= c2; h1 = h1 xor k1 }
            h1 = h1 xor length.toLong(); h2 = h2 xor length.toLong()
            h1 += h2; h2 += h1
            h1 = fmix(h1); h2 = fmix(h2)
            h1 += h2
            return if (h1 == Long.MIN_VALUE) Long.MAX_VALUE else h1 // Cassandra keeps MIN_VALUE for "before every token"
        }

        private fun fmix(k0: Long): Long {
            var k = k0
            k = k xor (k ushr 33); k *= -0xae502812aa7333L // 0xff51afd7ed558ccd
            k = k xor (k ushr 33); k *= -0x3b314601e57a13adL // 0xc4ceb9fe1a85ec53
            return k xor (k ushr 33)
        }
    }
}
