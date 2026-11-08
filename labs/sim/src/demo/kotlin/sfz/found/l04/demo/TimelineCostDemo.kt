package sfz.found.l04.demo

import kotlin.math.pow
import kotlin.random.Random

// Prices three home-timeline designs on a skewed follow graph of 100,000 users.
// Run from the labs folder:
//   ./gradlew :sim:demo -Pmain=sfz.found.l04.demo.TimelineCostDemoKt --console=plain -q
//   ./gradlew :sim:demo -Pmain=sfz.found.l04.demo.TimelineCostDemoKt --console=plain -q -Pargs='5000 60'
// The first argument is the hybrid's celebrity threshold (followers), the second the number of
// timeline reads per post. Everything is counted, not timed, so the output is the same on every machine.

const val USERS = 100_000
const val WRITES_PER_SECOND = 5_000.0      // what the fan-out workers can do together
const val DEADLINE_SECONDS = 5.0           // a post should reach every follower within this
const val REASONABLE_LIMIT = 2_000         // Bluesky's rule for heavy followers

fun main(args: Array<String>) {
    val threshold = args.getOrNull(0)?.toInt() ?: (WRITES_PER_SECOND * DEADLINE_SECONDS).toInt()
    val readsPerPost = args.getOrNull(1)?.toDouble() ?: 60.0

    val followees = skewedGraph(USERS)
    val followers = IntArray(USERS)
    for (list in followees) for (f in list) followers[f]++
    val follows = followees.map { it.size }

    println("load parameters of the network")
    println("  users                  %,d".format(USERS))
    println("  follow edges           %,d".format(follows.sum().toLong()))
    describe("  followers per account ", followers.toList())
    describe("  follows per account   ", follows)
    println()

    val celebrity = BooleanArray(USERS) { followers[it] > threshold }
    val keep = DoubleArray(USERS) { minOf(REASONABLE_LIMIT.toDouble() / maxOf(follows[it], 1), 1.0) }

    // writes caused by one post of each author, and lookups caused by one read of each reader
    val pullWrites = DoubleArray(USERS) { 1.0 }
    val pullReads = DoubleArray(USERS) { follows[it].toDouble() }
    val pushWrites = DoubleArray(USERS) { followers[it].toDouble() }
    val pushReads = DoubleArray(USERS) { 1.0 }
    val hybridWrites = DoubleArray(USERS)
    val hybridReads = DoubleArray(USERS) { 1.0 }
    for (reader in 0 until USERS) for (author in followees[reader]) {
        if (celebrity[author]) hybridReads[reader] += 1.0           // merged at read time
        else hybridWrites[author] += keep[reader]                    // fanned out, maybe sampled
    }
    for (author in 0 until USERS) if (celebrity[author]) hybridWrites[author] = 1.0

    println("                    writes per post     lookups per read   work per post     slowest")
    val reads = if (readsPerPost % 1.0 == 0.0) "%,.0f".format(readsPerPost) else "%.1f".format(readsPerPost)
    println("design                mean       max       mean      max   (%s reads)      delivery".format(reads))
    row("fan-out on read", pullWrites, pullReads, readsPerPost)
    row("fan-out on write", pushWrites, pushReads, readsPerPost)
    row("hybrid > %,d".format(threshold), hybridWrites, hybridReads, readsPerPost)
    println()
    println("celebrities (more than %,d followers): %d accounts".format(threshold, celebrity.count { it }))
    println("work per post = writes per post + reads per post x lookups per read")
    println("slowest delivery = most writes one post needs / %,.0f writes per second, with an empty queue".format(WRITES_PER_SECOND))
}

fun row(name: String, writes: DoubleArray, reads: DoubleArray, readsPerPost: Double) {
    val w = writes.average()
    val r = reads.average()
    println("%-17s %,8.1f %,9.0f %,10.1f %,8.0f %,14.0f %,12.1f s".format(
        name, w, writes.max(), r, reads.max(), w + readsPerPost * r, writes.max() / WRITES_PER_SECOND))
}

fun describe(label: String, values: List<Int>) {
    val s = values.sorted()
    fun p(q: Double) = s[((s.size - 1) * q).toInt()]
    println("%s mean %.1f   p50 %,d   p99 %,d   p99.9 %,d   max %,d".format(
        label, values.average(), p(0.5), p(0.99), p(0.999), s.last()))
}

/** The lab's FollowGraph.skewed: user 0 is the most popular account; the last 20 users follow 4,000 each. */
fun skewedGraph(size: Int, followsPerUser: Int = 50, heavyUsers: Int = 20, heavyFollows: Int = 4_000,
                exponent: Double = 0.8, seed: Long = 42): Array<IntArray> {
    val cdf = DoubleArray(size)
    var total = 0.0
    for (i in 0 until size) { total += 1.0 / (i + 1.0).pow(exponent); cdf[i] = total }
    val random = Random(seed)
    return Array(size) { user ->
        val want = if (user >= size - heavyUsers) heavyFollows else followsPerUser
        val picked = HashSet<Int>(want * 2)
        while (picked.size < want) {
            var target = cdf.binarySearch(random.nextDouble() * total)
            if (target < 0) target = -target - 1
            if (target != user) picked += target.coerceAtMost(size - 1)
        }
        picked.toIntArray()
    }
}
