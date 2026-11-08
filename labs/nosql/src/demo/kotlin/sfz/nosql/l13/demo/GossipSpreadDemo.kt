package sfz.nosql.l13.demo

import kotlin.math.ceil
import kotlin.math.log2
import kotlin.random.Random

/**
 * How many gossip rounds does one piece of news need to reach every node? Each round, every node
 * picks one random peer and the two swap what they know (push and pull, as Syn, Ack and Ack2 do).
 * Nodes act one after another within a round, in a random order. 50 runs per cluster size.
 * Every exchange is three messages, so a round costs 3 x N messages, however big the cluster.
 */
fun main() {
    println("nodes   log2(N)   rounds: fastest  median  slowest   messages per round")
    for (n in listOf(6, 60, 600, 6_000)) {
        val rounds = (1..50).map { seed -> roundsToSpread(n, Random(seed)) }.sorted()
        println(
            "%5d   %7d   %15d  %6d  %7d   %,d".format(
                n, ceil(log2(n.toDouble())).toInt(), rounds.first(), rounds[rounds.size / 2], rounds.last(), 3 * n
            )
        )
    }
}

/** Rounds until every one of [n] nodes knows the news that node 0 has at the start. */
private fun roundsToSpread(n: Int, random: Random): Int {
    val knows = BooleanArray(n).also { it[0] = true }
    var informed = 1
    var round = 0
    val order = (0 until n).toMutableList()
    while (informed < n) {
        round++
        order.shuffle(random)
        for (me in order) {
            var peer = random.nextInt(n - 1)
            if (peer >= me) peer++                  // anyone but me
            if (knows[me] != knows[peer]) {         // one of the two has the news: after Syn, Ack, Ack2 both do
                knows[me] = true; knows[peer] = true; informed++
            }
        }
    }
    return round
}
