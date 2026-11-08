package sfz.nosql.l18

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class SearchClusterTest {
    private fun SearchCluster.layout(): List<String> =
        copies.sortedWith(compareBy({ it.shard }, { !it.primary })).map { it.toString() }

    @Test
    fun `routingHash and routingNumShards are given and match OpenSearch`() {
        assertThat(routingHash("M-0042")).isEqualTo(1_428_742_541)
        assertThat(routingHash("M-0043")).isEqualTo(-870_690_191)
        assertThat(routingNumShards(3)).isEqualTo(768)   // what GET _cluster/state/metadata/merchants showed
        assertThat(routingNumShards(1)).isEqualTo(1024)
        assertThat(routingNumShards(5)).isEqualTo(640)
    }

    @Test
    fun `shardFor puts every merchant where the three-node cluster put it`() {
        // from GET merchants/_search_shards?routing=<id> on OpenSearch 3.9, index with 3 primaries
        val real = mapOf(
            "M-0042" to 2, "M-0043" to 2, "M-0044" to 0, "M-0045" to 0, "M-0046" to 0, "M-0047" to 2,
            "M-0048" to 2, "M-0049" to 0, "M-0050" to 1, "M-0051" to 0, "M-0052" to 0, "M-0053" to 1,
            "M-0054" to 2,
        )
        real.forEach { (id, shard) -> assertThat(shardFor(id, 3)).describedAs(id).isEqualTo(shard) }
        // the docs' shorthand, hash % 3, would put 7 of these 13 in the wrong shard
        assertThat(real.count { (id, shard) -> Math.floorMod(routingHash(id), 3) != shard }).isEqualTo(7)
    }

    @Test
    fun `shardFor keeps a shard's documents together when the index is split in two`() {
        // _split from 3 to 6 primaries: 768 slots either way, so shard s's documents land in 2s or 2s + 1
        val ids = (1..5_000).map { "M-%04d".format(it) }
        assertThat(ids).allSatisfy { assertThat(shardFor(it, 6) / 2).isEqualTo(shardFor(it, 3)) }
        // but a plain modulo would move most of them (lesson 5 of this track): 3 to 4 shards
        assertThat(ids.count { Math.floorMod(routingHash(it), 3) != Math.floorMod(routingHash(it), 4) }).isGreaterThan(3_500)
    }

    @Test
    fun `allocate never puts a replica next to its own primary and spreads the copies evenly`() {
        val c = SearchCluster(listOf("os1", "os2", "os3"))
        c.createIndex(primaries = 3, replicas = 1)
        assertThat(c.layout()).containsExactly("0p@os1", "0r@os2", "1p@os2", "1r@os3", "2p@os3", "2r@os1")
        assertThat(c.health()).isEqualTo(Health.GREEN)
        for (s in 0 until 3) assertThat(c.copiesOf(s).map { it.node }.toSet()).hasSize(2)
        assertThat(c.nodes.map { c.copiesOn(it).size }).containsExactly(2, 2, 2)
    }

    @Test
    fun `replicas that have nowhere to go stay unassigned, and the index is yellow`() {
        val one = SearchCluster(listOf("os1"))
        one.createIndex(primaries = 3, replicas = 1)
        assertThat(one.copies.filter { !it.primary }.map { it.node }).containsOnlyNulls()
        assertThat(one.health()).isEqualTo(Health.YELLOW)       // lesson 12's single node: every primary, no replica

        val two = SearchCluster(listOf("os1", "os2"))
        two.createIndex(primaries = 2, replicas = 2)            // 3 copies of each shard, 2 nodes
        assertThat(two.copies.count { it.node == null }).isEqualTo(2)
        assertThat(two.health()).isEqualTo(Health.YELLOW)

        val three = SearchCluster(listOf("os1", "os2", "os3"))
        three.createIndex(primaries = 2, replicas = 2)
        assertThat(three.health()).isEqualTo(Health.GREEN)
        assertThat(three.nodes.map { three.copiesOn(it).size }).containsExactly(2, 2, 2)
    }

    @Test
    fun `a node leaves, so its primary's replica is promoted and its lost copies wait, unassigned`() {
        val c = SearchCluster(listOf("os1", "os2", "os3"))
        c.createIndex(primaries = 3, replicas = 1)
        c.nodeLeft("os3")
        assertThat(c.nodes).containsExactly("os1", "os2")
        assertThat(c.primaryOf(2).node).isEqualTo("os1")        // the replica on os1 is the primary now
        assertThat(c.layout()).containsExactly("0p@os1", "0r@os2", "1p@os2", "1r@unassigned", "2p@os1", "2r@unassigned")
        assertThat(c.health()).isEqualTo(Health.YELLOW)         // all data still searchable, less redundancy
    }

    @Test
    fun `after the delay the manager copies new replicas and the index is green on two nodes`() {
        val c = SearchCluster(listOf("os1", "os2", "os3"))
        c.createIndex(primaries = 3, replicas = 1)
        c.nodeLeft("os3")
        c.allocate()                                            // delayed_timeout has passed
        assertThat(c.layout()).containsExactly("0p@os1", "0r@os2", "1p@os2", "1r@os1", "2p@os1", "2r@os2")
        assertThat(c.health()).isEqualTo(Health.GREEN)
        // a second node goes: one node can't hold two copies of a shard, so yellow is the best it can do
        c.nodeLeft("os2")
        c.allocate()
        assertThat(c.copies.filter { it.primary }.map { it.node }).containsOnly("os1")
        assertThat(c.health()).isEqualTo(Health.YELLOW)
    }

    @Test
    fun `two nodes lost before any copy is rebuilt leave a shard with no copy, and the index turns red`() {
        val c = SearchCluster(listOf("os1", "os2", "os3"))
        c.createIndex(primaries = 3, replicas = 1)
        c.nodeLeft("os2")                                       // held 1p and 0r
        c.nodeLeft("os3")                                       // held 1r (just promoted) and 2p
        assertThat(c.primaryOf(1).node).isNull()
        assertThat(c.health()).isEqualTo(Health.RED)
        c.nodeJoined("os4")                                     // an empty node can't bring shard 1's data back
        assertThat(c.health()).isEqualTo(Health.RED)
        assertThat(c.copiesOn("os4").map { it.shard }).containsExactlyInAnyOrder(0, 2)
    }

    private val merchants = mapOf(
        "M-0042" to "Northwind Bikes, bike repairs and spare parts", "M-0043" to "Northwind Coffee",
        "M-0044" to "City Bike Rental", "M-0045" to "Bikes and Boards Outlet, used bikes",
        "M-0046" to "Harbour Fish Market", "M-0047" to "Station Bakery", "M-0048" to "Riverside Books",
        "M-0049" to "Moor Cycle Works", "M-0050" to "Old Mill Pharmacy", "M-0051" to "Quayside Florist",
        "M-0052" to "Abbey Garage", "M-0053" to "Dales Outdoor Shop",
    )

    /** A stand-in for BM25: how many times the text contains each query word. */
    private fun matches(vararg words: String): (String) -> Double = { text ->
        val tokens = text.lowercase().split(Regex("[^a-z0-9]+"))
        words.sumOf { w -> tokens.count { it == w }.toDouble() }
    }

    @Test
    fun `search asks every shard, merges their best hits and fetches only the page`() {
        val idx = ShardedIndex(primaries = 3)
        merchants.forEach { (id, name) -> idx.index(id, name) }
        assertThat((0 until 3).map { idx.docsIn(it) }).containsExactly(6, 2, 4)   // as _cat/shards showed
        val hits = idx.search(matches("northwind", "bikes"), size = 3)
        // M-0042 and M-0045 both score 2 and tie on score: the id decides
        assertThat(hits.map { it.first.id }).containsExactly("M-0042", "M-0045", "M-0043")
        assertThat(hits.first().first.shard).isEqualTo(2)
        assertThat(hits.first().second).isEqualTo("Northwind Bikes, bike repairs and spare parts")
        assertThat(idx.shardRequests).isEqualTo(3)
        assertThat(idx.hitsSentToCoordinator).isEqualTo(3)  // shard 0 had one match, shard 2 two, shard 1 none
        assertThat(idx.documentsFetched).isEqualTo(3)
        assertThat(idx.search(matches("scooter"))).isEmpty()
        assertThat(idx.documentsFetched).isEqualTo(0)
    }

    @Test
    fun `a deep page costs every shard from + size hits`() {
        val idx = ShardedIndex(primaries = 3)
        (1..600).forEach { idx.index("M-%04d".format(it), "merchant number $it") }
        val score: (String) -> Double = { it.substringAfterLast(' ').toDouble() }   // higher number, better
        val page = idx.search(score, from = 100, size = 10)
        assertThat(page.map { it.first.id }).containsExactlyElementsOf((500 downTo 491).map { "M-%04d".format(it) })
        assertThat(idx.shardRequests).isEqualTo(3)
        assertThat(idx.hitsSentToCoordinator).isEqualTo(3 * 110)   // each shard sends its top 110
        assertThat(idx.documentsFetched).isEqualTo(10)
    }
}
