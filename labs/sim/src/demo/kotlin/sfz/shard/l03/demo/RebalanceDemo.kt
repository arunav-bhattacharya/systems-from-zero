package sfz.shard.l03.demo

import java.nio.ByteBuffer
import java.security.MessageDigest
import java.util.TreeMap

fun md5(key: String): Long = ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(key.toByteArray())).long

/** Ten nodes hold 100,000 payment keys. An eleventh joins. How many keys move, and who sends them? */
fun main() {
    val ten = (1..10).map { "node-%02d".format(it) }
    val eleven = ten + "node-11"
    val keys = (0 until 100_000).map { "pay-$it" }

    fun report(name: String, before: (String) -> String, after: (String) -> String) {
        val moved = keys.filter { before(it) != after(it) }
        val senders = moved.map(before).toSet().size
        val toNew = moved.count { after(it) == "node-11" }
        println("%-26s %,6d keys move (%4.1f%%), %,6d of them to node-11, sent by %2d %s"
            .format(name, moved.size, moved.size / 1_000.0, toNew, senders, if (senders == 1) "node" else "nodes"))
    }

    // lesson 1: node = hash mod N
    report("hash mod N", { ten[Math.floorMod(md5(it), 10L).toInt()] }, { eleven[Math.floorMod(md5(it), 11L).toInt()] })

    // fixed partitions: 1,000 of them; a key's partition never changes, whole partitions change node
    val owner = Array(1_000) { ten[it % 10] }
    val before = owner.copyOf()
    var given = 0
    while (given < 1_000 / 11) { // node-11 takes 90 partitions, one at a time from the busiest node
        val donor = ten.maxBy { n -> owner.count { it == n } }
        owner[owner.indices.last { owner[it] == donor }] = "node-11"
        given++
    }
    val partition = { key: String -> Math.floorMod(md5(key), 1_000L).toInt() }
    report("1,000 fixed partitions", { before[partition(it)] }, { owner[partition(it)] })

    // lesson 2: a ring with T tokens per node
    for (t in listOf(1, 16)) {
        fun ring(nodes: List<String>) = TreeMap<Long, String>().apply { nodes.forEach { n -> repeat(t) { put(md5("$n#$it"), n) } } }
        val r10 = ring(ten)
        val r11 = ring(eleven)
        val owner = { r: TreeMap<Long, String>, k: String -> (r.ceilingEntry(md5(k)) ?: r.firstEntry()).value }
        report("ring, $t token(s) per node", { owner(r10, it) }, { owner(r11, it) })
    }
}
