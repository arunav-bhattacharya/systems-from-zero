package sfz.shard.l04.demo

import java.nio.ByteBuffer
import java.security.MessageDigest

fun shardFor(key: String, shards: Int): Int =
    Math.floorMod(ByteBuffer.wrap(MessageDigest.getInstance("MD5").digest(key.toByteArray())).long, shards.toLong()).toInt()

/** 10,000 payments over 1,000 cards, sharded by payment id. The fraud check asks: what has card-242 done? */
fun main() {
    val payments = (0 until 10_000).map { "pay-$it" to "card-${it % 1_000}" }
    for (shards in listOf(8, 32)) {
        val rowShard = payments.associate { (id, _) -> id to shardFor(id, shards) }
        val card242 = payments.filter { it.second == "card-242" }.map { it.first }
        println("$shards shards; card-242 has ${card242.size} payments, on shards ${card242.map { rowShard.getValue(it) }.sorted()}")
        println("  find pay-1234 by id:            asks 1 shard")
        // local index: each shard indexes its own rows, so all of them must be asked
        println("  find by card, local index:      asks $shards shards; each payment writes 1 shard")
        // global index: all of card-242's entries sit on one index shard, then fetch the rows
        val rowShards = card242.map { rowShard.getValue(it) }.toSet().size
        println("  find by card, global index:     asks 1 index shard + $rowShards row shards; each payment writes 2 shards")
        println("  2,000 fraud checks a second cost ${"%,d".format(2_000 * shards)} shard requests with the local index, ${"%,d".format(2_000 * (1 + rowShards))} with the global one")
    }
}
