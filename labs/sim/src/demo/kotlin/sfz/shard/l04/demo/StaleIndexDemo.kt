package sfz.shard.l04.demo

import java.util.Random

/**
 * A model of an asynchronous global index, on virtual time. Each index entry lands some time after its
 * row: here 30 to 120 ms, and 1 time in 50 it takes 600 ms (a busy index shard). These lags are made
 * up for the model; DynamoDB only promises "a fraction of a second, under normal conditions".
 * The fraud check reads the index some milliseconds after each payment. How often is it missing?
 */
fun main() {
    val rnd = Random(7)
    val lags = List(10_000) { if (rnd.nextInt(50) == 0) 600L else 30L + rnd.nextInt(91) }
    println("check runs after   index still missing the payment")
    for (after in listOf(10L, 50L, 100L, 250L, 1_000L)) {
        val missing = lags.count { it > after }
        println("%13d ms   %,6d of 10,000 (%.1f%%)".format(after, missing, missing / 100.0))
    }
    println("reading the row by its key: 0 of 10,000 missing, at any time")
}
