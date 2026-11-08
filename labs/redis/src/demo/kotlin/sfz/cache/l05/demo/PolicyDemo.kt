package sfz.cache.l05.demo

import java.util.Random
import kotlin.math.pow

/** FIFO, LRU and SIEVE on the same Zipf requests, without and with one-time scans mixed in. No Docker needed. */
fun main() {
    val n = 100_000
    val zipf = zipfTrace(n, 1.0, 1_000_000, 7)
    val scans = withScans(zipf, n)
    println("miss ratio on the Zipf requests (alpha 1.0, 100,000 keys)")
    println("cache     workload        FIFO     LRU   SIEVE")
    for (size in listOf(1_000, 10_000)) {
        for ((name, trace) in listOf("Zipf" to zipf, "Zipf + scans" to scans)) {
            println("%,6d    %-12s  %6.1f%%  %5.1f%%  %5.1f%%".format(size, name,
                100 * missRatio(trace, Fifo(size), n), 100 * missRatio(trace, Lru(size), n), 100 * missRatio(trace, Sieve(size), n)))
        }
    }
}

private interface Policy { fun access(key: Int): Boolean }

/** Misses among the Zipf requests after a warm-up; scan keys (above n) are replayed but not counted. */
private fun missRatio(trace: IntArray, policy: Policy, n: Int): Double {
    var counted = 0L
    var misses = 0L
    trace.forEachIndexed { i, key ->
        val hit = policy.access(key)
        if (i >= trace.size / 5 && key <= n) {
            counted++
            if (!hit) misses++
        }
    }
    return misses.toDouble() / counted
}

/** FIFO: evict the key that was inserted first; a hit changes nothing. */
private class Fifo(val capacity: Int) : Policy {
    private val queue = ArrayDeque<Int>()
    private val cached = HashSet<Int>()
    override fun access(key: Int): Boolean {
        if (key in cached) return true
        if (cached.size >= capacity) cached.remove(queue.removeFirst())
        queue.addLast(key)
        cached.add(key)
        return false
    }
}

/** LRU: a hit moves the key to the newest end; evict from the oldest end. */
private class Lru(val capacity: Int) : Policy {
    private val map = object : LinkedHashMap<Int, Boolean>(16, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Int, Boolean>) = size > capacity
    }
    override fun access(key: Int): Boolean {
        if (map[key] != null) return true
        map[key] = true
        return false
    }
}

/** SIEVE: one FIFO list and a visited bit. A hit only sets the bit; the hand evicts the first unvisited key. */
private class Sieve(val capacity: Int) : Policy {
    private class Node(val key: Int) {
        var visited = false
        var newer: Node? = null
        var older: Node? = null
    }
    private val nodes = HashMap<Int, Node>()
    private var head: Node? = null                      // newest
    private var tail: Node? = null                      // oldest
    private var hand: Node? = null

    override fun access(key: Int): Boolean {
        nodes[key]?.let {
            it.visited = true                           // no move, no lock needed in a concurrent version
            return true
        }
        if (nodes.size >= capacity) evict()
        val node = Node(key)                            // new keys always enter at the head
        node.older = head
        head?.newer = node
        head = node
        if (tail == null) tail = node
        nodes[key] = node
        return false
    }

    private fun evict() {
        var o = hand ?: tail!!
        while (o.visited) {                             // spare visited keys, clear their bit, keep walking
            o.visited = false
            o = o.newer ?: tail!!                       // past the head: start again from the tail
        }
        hand = o.newer                                  // the next eviction resumes here
        if (o.newer != null) o.newer!!.older = o.older else head = o.older
        if (o.older != null) o.older!!.newer = o.newer else tail = o.newer
        nodes.remove(o.key)
    }
}

/** After every 50,000 requests, a one-time scan of 5,000 keys nobody asks for again. */
private fun withScans(zipf: IntArray, n: Int): IntArray {
    val out = ArrayList<Int>(zipf.size + zipf.size / 10)
    var next = n + 1
    zipf.forEachIndexed { i, key ->
        out += key
        if ((i + 1) % 50_000 == 0) repeat(5_000) { out += next++ }
    }
    return out.toIntArray()
}

private fun zipfTrace(n: Int, alpha: Double, length: Int, seed: Long): IntArray {
    val total = (1..n).sumOf { it.toDouble().pow(-alpha) }
    var running = 0.0
    val cdf = DoubleArray(n) { running += (it + 1.0).pow(-alpha) / total; running }
    cdf[n - 1] = 1.0
    val random = Random(seed)
    return IntArray(length) {
        val k = cdf.binarySearch(random.nextDouble())
        (if (k >= 0) k else -k - 1) + 1
    }
}
