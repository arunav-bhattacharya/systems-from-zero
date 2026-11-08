package sfz.nosql.l17

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class RecordStoreTest {
    private val ACCOUNT = 0
    private val DEVICE = 1
    private val PHONE = 2
    private val USES = 0
    private val TRANSFERRED_TO = 1

    /** The fraud graph of lesson 11, created in exactly the order `env/neo4j/nosql-11-fraud.cypher` creates it. */
    private class Fraud(val ids: Map<String, Long>) {
        operator fun get(name: String): Long = ids.getValue(name)
        fun name(id: Long): String = ids.entries.first { it.value == id }.key
    }

    private val accounts = listOf("A-1001", "A-2002", "A-3101", "A-3102", "A-3103", "A-3104", "A-3105",
        "A-4001", "A-4002", "A-4003", "A-4004", "A-4005", "A-4006")
    private val devices = listOf("D-11", "D-22", "D-77", "D-81", "D-40", "D-41", "D-42", "D-43", "D-KIOSK")
    private val phones = listOf("P-0111", "P-0122", "P-0177", "P-0181", "P-0199", "P-0140")
    private val uses = listOf(
        "A-1001" to "D-11", "A-1001" to "P-0111", "A-2002" to "D-22", "A-2002" to "P-0122",
        "A-3101" to "D-77", "A-3101" to "P-0177", "A-3102" to "D-77", "A-3102" to "P-0177",
        "A-3102" to "P-0199", "A-3103" to "P-0199", "A-3103" to "D-81", "A-3103" to "P-0181",
        "A-3104" to "D-81", "A-3104" to "P-0181", "A-3105" to "D-81",
        "A-4001" to "D-40", "A-4001" to "P-0140", "A-4002" to "D-41", "A-4003" to "D-42",
        "A-4005" to "D-43", "A-4006" to "D-43",
        "A-1001" to "D-KIOSK", "A-2002" to "D-KIOSK", "A-4002" to "D-KIOSK", "A-4003" to "D-KIOSK",
        "A-3103" to "D-KIOSK",
    )
    private val transfers = listOf(
        "A-3101" to "A-3103", "A-3103" to "A-3104", "A-3104" to "A-3101",
        "A-3102" to "A-3105", "A-3105" to "A-4004", "A-4004" to "A-3103", "A-3103" to "A-3102",
        "A-1001" to "A-2002", "A-2002" to "A-1001", "A-4001" to "A-1001", "A-4005" to "A-4006",
    )

    private fun fraudGraph(store: RecordStore): Fraud {
        val ids = linkedMapOf<String, Long>()
        accounts.forEach { ids[it] = store.createNode(ACCOUNT) }
        devices.forEach { ids[it] = store.createNode(DEVICE) }
        phones.forEach { ids[it] = store.createNode(PHONE) }
        uses.forEach { (a, x) -> store.createRelationship(ids.getValue(a), ids.getValue(x), USES) }
        transfers.forEach { (a, b) -> store.createRelationship(ids.getValue(a), ids.getValue(b), TRANSFERRED_TO) }
        return Fraud(ids)
    }

    private fun hex(s: String): ByteArray = s.split(" ").filter { it.isNotBlank() }.map { it.toInt(16).toByte() }.toByteArray()

    /** Bytes [from, to) blanked out, for fields this model doesn't store (property pointers). */
    private fun ByteArray.without(from: Int, to: Int): List<Byte> = mapIndexed { i, b -> if (i in from until to) 0 else b }

    @Test
    fun `locate is given and puts records where Neo4j's aligned format puts them`() {
        assertThat(locate(2, NODE_RECORD_SIZE).fileOffset).isEqualTo(30)
        assertThat(locate(28, REL_RECORD_SIZE).fileOffset).isEqualTo(952)
        // 546 node records fit in a page (546 x 15 = 8,190), so node 546 starts page 1, after 2 bytes of padding
        assertThat(locate(546, NODE_RECORD_SIZE)).isEqualTo(Location(page = 1, offsetInPage = 0, fileOffset = 8192))
        assertThat(locate(240, REL_RECORD_SIZE)).isEqualTo(Location(page = 1, offsetInPage = 0, fileOffset = 8192))
    }

    @Test
    fun `alignedStoreBytes rounds up to whole pages, as the files on disk show`() {
        assertThat(alignedStoreBytes(28, NODE_RECORD_SIZE)).isEqualTo(8_192)      // the fraud graph's nodes
        assertThat(alignedStoreBytes(2_037, REL_RECORD_SIZE)).isEqualTo(73_728)  // after 2,000 more transfers
        assertThat(alignedStoreBytes(546, NODE_RECORD_SIZE)).isEqualTo(8_192)
        assertThat(alignedStoreBytes(547, NODE_RECORD_SIZE)).isEqualTo(16_384)
        assertThat(alignedStoreBytes(0, REL_RECORD_SIZE)).isEqualTo(8_192)
        // 50 million accounts: 91,576 pages, about 750 MB
        assertThat(alignedStoreBytes(50_000_000, NODE_RECORD_SIZE)).isEqualTo(91_576L * 8_192)
    }

    @Test
    fun `createRelationship puts the new relationship at the head of both chains`() {
        val store = RecordStore()
        val a = store.createNode(ACCOUNT)
        val b = store.createNode(DEVICE)
        val c = store.createNode(PHONE)
        val r0 = store.createRelationship(a, b, USES)
        val r1 = store.createRelationship(a, c, USES)
        assertThat(r0).isEqualTo(0)
        assertThat(r1).isEqualTo(1)
        assertThat(store.readNode(a).nextRel).isEqualTo(r1)
        assertThat(store.readNode(b).nextRel).isEqualTo(r0)
        val head = store.readRel(r1)
        assertThat(head.firstNode).isEqualTo(a)
        assertThat(head.secondNode).isEqualTo(c)
        assertThat(head.firstNext).isEqualTo(r0)       // a's chain continues to the older relationship
        assertThat(head.firstPrev).isEqualTo(2)        // the head stores a's degree
        assertThat(head.secondNext).isEqualTo(NONE)    // c has only this one
        assertThat(head.secondPrev).isEqualTo(1)
        assertThat(head.firstInFirstChain && head.firstInSecondChain).isTrue()
        val old = store.readRel(r0)
        assertThat(old.firstPrev).isEqualTo(r1)        // doubly linked: back to the new head
        assertThat(old.firstInFirstChain).isFalse()    // no longer the head of a's chain
        assertThat(old.firstInSecondChain).isTrue()    // still the head of b's chain
        assertThat(old.secondPrev).isEqualTo(1)
    }

    @Test
    fun `the fraud graph's records come out byte for byte as Neo4j 2026_10 wrote them`() {
        val store = RecordStore()
        val g = fraudGraph(store)
        assertThat(g["A-3101"]).isEqualTo(2)
        // dumped with od from neostore.nodestore.db and neostore.relationshipstore.db (property pointers blanked)
        val node2 = hex("01 00 00 00 1c 00 00 00 0a 00 00 00 00 10 00")
        val rel28 = hex("01 00 00 00 05 00 00 00 02 00 00 00 01 00 00 00 04 00 00 00 1b 00 00 00 04 00 00 00 1a 00 00 00 26 03")
        val rel26 = hex("01 00 00 00 02 00 00 00 04 00 00 00 01 00 00 00 1c 00 00 00 05 00 00 00 1b 00 00 00 19 00 00 00 24 00")
        val rel5 = hex("01 00 00 00 02 00 00 00 18 00 00 00 00 00 00 00 1a 00 00 00 04 00 00 00 07 ff ff ff ff ff ff ff ff 00")
        val rel4 = hex("01 00 00 00 02 00 00 00 0f 00 00 00 00 00 00 00 05 ff ff ff ff 00 00 00 06 ff ff ff ff ff ff ff ff 00")
        assertThat(store.nodeBytes(2).without(5, 9)).isEqualTo(node2.without(5, 9))
        assertThat(store.relBytes(28).without(29, 33)).isEqualTo(rel28.without(29, 33))
        assertThat(store.relBytes(26).without(29, 33)).isEqualTo(rel26.without(29, 33))
        assertThat(store.relBytes(5).toList()).isEqualTo(rel5.toList())
        assertThat(store.relBytes(4).toList()).isEqualTo(rel4.toList())
    }

    @Test
    fun `relationshipsOf walks one chain, newest first, one record read per relationship`() {
        val store = RecordStore()
        val g = fraudGraph(store)
        store.resetCounters()
        assertThat(store.relationshipsOf(g["A-3101"]).map { it.id }).containsExactly(28L, 26L, 5L, 4L)
        assertThat(store.recordReads).isEqualTo(5)     // the node, then four relationships
        // the kiosk is the second node of each of its relationships, so the walk follows secondNext
        assertThat(store.relationshipsOf(g["D-KIOSK"]).map { it.id }).containsExactly(25L, 24L, 23L, 22L, 21L)
        // A-3103 is the first node of some relationships and the second of others: one chain all the same
        assertThat(store.relationshipsOf(g["A-3103"]).map { it.id }).containsExactly(32L, 31L, 27L, 26L, 25L, 11L, 10L, 9L)
    }

    @Test
    fun `degree comes from the head of the chain in at most two record reads`() {
        val store = RecordStore()
        val g = fraudGraph(store)
        store.resetCounters()
        assertThat(store.degree(g["A-3101"])).isEqualTo(4)
        assertThat(store.recordReads).isEqualTo(2)
        assertThat(store.degree(g["D-KIOSK"])).isEqualTo(5)
        assertThat(store.degree(g["A-3103"])).isEqualTo(8)
        assertThat(store.degree(g["A-4004"])).isEqualTo(2)
        val lonely = store.createNode(ACCOUNT)
        store.resetCounters()
        assertThat(store.degree(lonely)).isEqualTo(0)
        assertThat(store.recordReads).isEqualTo(1)
    }

    @Test
    fun `expand walks the ring out from A-3101, hop by hop`() {
        val store = RecordStore()
        val g = fraudGraph(store)
        val viaIdentifiers = store.expand(g["A-3101"], hops = 4, type = USES).mapKeys { g.name(it.key) }
        assertThat(viaIdentifiers).containsExactlyInAnyOrderEntriesOf(
            mapOf("D-77" to 1, "P-0177" to 1, "A-3102" to 2, "P-0199" to 3, "A-3103" to 4),
        )
        val oneHop = store.expand(g["A-3101"], hops = 1).mapKeys { g.name(it.key) }
        assertThat(oneHop.keys).containsExactlyInAnyOrder("D-77", "P-0177", "A-3103", "A-3104")
        assertThat(store.expand(g["A-3101"], hops = 0)).isEmpty()
    }

    @Test
    fun `a hop costs the same in a big graph, while every index lookup gets deeper`() {
        val store = RecordStore(maxNodes = 30_000, maxRelationships = 120_000)
        val g = fraudGraph(store)
        val join = JoinTableGraph()
        uses.forEach { (a, x) -> join.addRelationship(g[a], g[x], USES) }
        transfers.forEach { (a, b) -> join.addRelationship(g[a], g[b], TRANSFERRED_TO) }

        fun walk(): Pair<Long, Long> {
            store.resetCounters(); join.resetCounters()
            val a = store.expand(g["A-3101"], hops = 3)
            val b = join.expand(g["A-3101"], hops = 3)
            assertThat(a).isEqualTo(b)                  // same answer either way
            return store.recordReads to join.pageReads
        }
        val (smallReads, smallPages) = walk()

        // 100,000 transfers among 20,000 other accounts that have nothing to do with the ring
        val others = (0 until 20_000).map { store.createNode(ACCOUNT) }
        val rnd = java.util.Random(17)
        repeat(100_000) {
            val a = others[rnd.nextInt(others.size)]
            var b = others[rnd.nextInt(others.size)]
            if (b == a) b = others[(others.indexOf(a) + 1) % others.size]
            store.createRelationship(a, b, TRANSFERRED_TO)
            join.addRelationship(a, b, TRANSFERRED_TO)
        }
        val (bigReads, bigPages) = walk()

        assertThat(bigReads).isEqualTo(smallReads)      // the walk touched the same records
        assertThat(join.height).isEqualTo(3)            // 100,037 rows: a tree three levels deep
        assertThat(bigPages).isEqualTo(smallPages * 3)  // every lookup now descends three levels instead of one
    }
}
