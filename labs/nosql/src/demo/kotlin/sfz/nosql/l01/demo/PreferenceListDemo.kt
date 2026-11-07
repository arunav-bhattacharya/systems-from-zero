package sfz.nosql.l01.demo

import java.math.BigInteger
import java.security.MessageDigest

// Dynamo hashes keys with MD5 onto a ring of 2^128 positions
private val RING: BigInteger = BigInteger.ONE.shiftLeft(128)

private fun md5(text: String): BigInteger =
    BigInteger(1, MessageDigest.getInstance("MD5").digest(text.toByteArray()))

/** Where on the ring a hash sits, as a percentage of the way round. */
private fun percent(position: BigInteger): String =
    "%5.1f%%".format(position.multiply(BigInteger.valueOf(1000)).divide(RING).toInt() / 10.0)

/** Six nodes, one token each. Which nodes store a key, and what changes when one is down. */
fun main() {
    // each node takes the ring position of the hash of its name
    val nodes = listOf("node-A", "node-B", "node-C", "node-D", "node-E", "node-F")
        .map { it to md5(it) }
        .sortedBy { it.second }
    println("Ring (clockwise):")
    nodes.forEach { (name, token) -> println("  $name at ${percent(token)}") }

    // walk clockwise from the key's position; skip nodes that are down
    fun walk(key: String, down: Set<String> = emptySet()): List<String> {
        val position = md5(key)
        val start = nodes.indexOfFirst { it.second >= position }.let { if (it < 0) 0 else it } // wrap past 100%
        return (nodes.indices).map { nodes[(start + it) % nodes.size].first }.filter { it !in down }
    }

    val n = 3
    for (key in listOf("pay-81723", "pay-81724", "ACCT#A-1001")) {
        println("$key hashes to ${percent(md5(key))}: stored on ${walk(key).take(n)}")
    }

    // one node is down: the write goes to the first N HEALTHY nodes (a sloppy quorum)
    val key = "pay-81723"
    val home = walk(key).take(n)
    val dead = home.first()
    val healthy = walk(key, down = setOf(dead)).take(n)
    val stranger = healthy.single { it !in home }
    println("$dead is down. $key goes to $healthy; $stranger keeps a hint for $dead")
}
