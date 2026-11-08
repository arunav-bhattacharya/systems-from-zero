package sfz.derive.l05.demo

// The demos carry their own copy of the lab's model, with the exercises finished.
// Do the lab first if you want to write the audit, the Merkle tree and the hash chain yourself.

import java.nio.ByteBuffer
import java.security.MessageDigest
import kotlin.random.Random

/** One record of the ledger log: [cents] added to (or, if negative, taken from) [account]. */
data class Posting(val offset: Int, val account: String, val cents: Long)

fun account(i: Int) = "acct-%03d".format(i)

/** A seeded ledger log (finished): [n] postings over [accounts] accounts, amounts between -50.00 and +99.99. */
object Ledger {
    fun log(seed: Long, n: Int = 5_000, accounts: Int = 500): List<Posting> {
        val rnd = Random(seed)
        return (0 until n).map { i ->
            val cents = if (rnd.nextInt(3) == 0) -(1 + rnd.nextInt(5_000)).toLong() else (1 + rnd.nextInt(9_999)).toLong()
            Posting(i, account(rnd.nextInt(accounts)), cents)
        }
    }
}

/** A bug in the live consumer that keeps the `balances` view. Each one leaves a different fingerprint. */
sealed interface Fault {
    /** The consumer's error handler swallows every [n]th record: it never reaches the view. */
    data class DropEvery(val n: Int) : Fault

    /** After a crash the consumer reads these offsets again and adds them again: `balance += cents` is not idempotent. */
    data class Redeliver(val offsets: Set<Int>) : Fault

    /** A mercurial core or a bad migration flips one bit of one stored balance, after the fact. */
    data class FlipBit(val account: String, val bit: Int) : Fault

    /** A schema change stores amounts in whole units from offset [from] on: the cents are cut off. */
    data class TruncateCents(val from: Int) : Fault
}

/**
 * The live consumer (finished). It reads the log once, in order, and keeps a balance per account,
 * with [faults] injected. Nothing in it throws or logs: every fault here is silent.
 */
fun liveBalances(log: List<Posting>, vararg faults: Fault): Map<String, Long> {
    val view = sortedMapOf<String, Long>()
    val drop = faults.filterIsInstance<Fault.DropEvery>().firstOrNull()
    val redeliver = faults.filterIsInstance<Fault.Redeliver>().flatMap { it.offsets }.toSet()
    val truncateFrom = faults.filterIsInstance<Fault.TruncateCents>().firstOrNull()?.from ?: Int.MAX_VALUE
    for (p in log) {
        if (drop != null && (p.offset + 1) % drop.n == 0) continue                  // swallowed by a catch block
        val cents = if (p.offset >= truncateFrom) p.cents / 100 * 100 else p.cents  // 12.34 stored as 12.00
        val times = if (p.offset in redeliver) 2 else 1
        repeat(times) { view[p.account] = (view[p.account] ?: 0L) + cents }
    }
    for (f in faults.filterIsInstance<Fault.FlipBit>()) {
        view[f.account] = (view[f.account] ?: 0L) xor (1L shl f.bit)                // silent corruption at rest
    }
    return view
}

/** SHA-256 over the concatenation of [parts]. */
fun sha256(vararg parts: ByteArray): ByteArray {
    val md = MessageDigest.getInstance("SHA-256")
    for (p in parts) md.update(p)
    return md.digest()
}

fun ByteArray.hex(): String = joinToString("") { "%02x".format(it) }

/** One account where the live view and the recomputed view disagree. A side that has no row is null. */
data class Drift(val account: String, val live: Long?, val expected: Long?) {
    /** How far the live view is off: live minus expected, with a missing row counted as 0. */
    val delta: Long get() = (live ?: 0L) - (expected ?: 0L)
}

/**
 * Exercise 1. Recompute the balances view from the log, from offset 0: the sum of the postings
 * of each account. This is the same derivation the live consumer runs, as a pure function of an
 * immutable log, so it gives the same answer every time it runs.
 */
fun recompute(log: List<Posting>): Map<String, Long> {
    val view = sortedMapOf<String, Long>()
    for (p in log) view[p.account] = (view[p.account] ?: 0L) + p.cents   // a fold: no side effects
    return view
}

/**
 * Exercise 2. Compare a live view with the recomputed one, key by key. Return one [Drift] for
 * every account whose values differ or that is missing on one side, sorted by account.
 */
fun diff(live: Map<String, Long>, expected: Map<String, Long>): List<Drift> =
    (live.keys + expected.keys).toSortedSet()
        .filter { live[it] != expected[it] }                         // a missing row is a difference too
        .map { Drift(it, live[it], expected[it]) }

/**
 * A Merkle tree over a key-value view, cut into [leaves] key ranges (a power of two).
 *
 * The tree is stored as an array, like a binary heap: `nodes[1]` is the root, node `i` has the
 * children `2i` and `2i + 1`, and the leaves are `nodes[leaves]` to `nodes[2 * leaves - 1]`.
 * Leaf `k` is the hash of every entry whose key falls in range `k` (finished, see [leafHash]).
 * Every other node is the hash of its two children.
 */
class MerkleTree(view: Map<String, Long>, val leaves: Int = 1_024) {
    init {
        require(leaves > 0 && leaves and (leaves - 1) == 0) { "leaves must be a power of two" }
    }

    val nodes: Array<ByteArray> = Array(2 * leaves) { ByteArray(0) }

    init {
        val buckets = Array(leaves) { sortedMapOf<String, Long>() }
        for ((k, v) in view) buckets[leafOf(k, leaves)][k] = v
        for (i in 0 until leaves) nodes[leaves + i] = leafHash(buckets[i])
        buildInternalNodes()
    }

    val root: ByteArray get() = nodes[1]

    /**
     * Exercise 3. Fill in every internal node, from the bottom up: for `i` from `leaves - 1` down
     * to 1, `nodes[i] = sha256(nodes[2i], nodes[2i + 1])`. Bottom up, because a parent needs its
     * children first.
     */
    private fun buildInternalNodes() {
        for (i in leaves - 1 downTo 1) nodes[i] = sha256(nodes[2 * i], nodes[2 * i + 1])
    }

    companion object {
        /** Which key range a key falls in: the first 4 bytes of SHA-256(key), modulo [leaves]. */
        fun leafOf(key: String, leaves: Int): Int =
            Math.floorMod(ByteBuffer.wrap(sha256(key.toByteArray())).int, leaves)

        /** The hash of one range: SHA-256 over "key=value\n" for each entry, in key order. An empty range hashes "" . */
        fun leafHash(entries: Map<String, Long>): ByteArray =
            sha256(entries.entries.joinToString("") { "${it.key}=${it.value}\n" }.toByteArray())
    }
}

/** The result of comparing two trees: the ranges that differ, and how many node pairs were compared. */
data class MerkleDiff(val leaves: List<Int>, val comparisons: Int)

/**
 * Exercise 4. Find the key ranges where [a] and [b] differ, without looking at every range.
 *
 * Start at the root. Compare the node in both trees (count one comparison). If the hashes are
 * equal, everything below is equal: stop. If they differ and the node is a leaf, record its range
 * number (`node - leaves`). Otherwise descend into both children. Return the ranges in increasing
 * order. Both trees must have the same number of leaves.
 */
fun compare(a: MerkleTree, b: MerkleTree): MerkleDiff {
    require(a.leaves == b.leaves) { "trees must have the same shape" }
    val different = ArrayList<Int>()
    var comparisons = 0
    fun visit(node: Int) {
        comparisons++
        if (a.nodes[node].contentEquals(b.nodes[node])) return     // equal hashes: the whole subtree matches
        if (node >= a.leaves) { different += node - a.leaves; return }
        visit(2 * node)                                            // left child first keeps the ranges sorted
        visit(2 * node + 1)
    }
    visit(1)
    return MerkleDiff(different, comparisons)
}

/** One entry of a hash-chained log. [hash] = SHA-256([prev] followed by the UTF-8 bytes of [payload]). */
class Entry(val index: Int, val payload: String, val prev: ByteArray, val hash: ByteArray)

/**
 * An append-only log where every entry carries the hash of the one before it. Change any old
 * entry and its hash no longer matches, and neither does the `prev` of the entry after it. The
 * last entry's hash, the [head], stands for the whole history: publish it somewhere the log's
 * owner can't rewrite, and anyone can check the log against it later.
 */
class HashChain {
    private val entries = ArrayList<Entry>()

    val size: Int get() = entries.size

    /** The hash of the newest entry, or [GENESIS] for an empty chain. */
    val head: ByteArray get() = entries.lastOrNull()?.hash ?: GENESIS

    fun entry(i: Int): Entry = entries[i]

    /** Exercise 5. Append [payload]: prev is the current [head], hash is `sha256(prev, payload bytes)`. */
    fun append(payload: String): Entry {
        val prev = head
        val e = Entry(entries.size, payload, prev, sha256(prev, payload.toByteArray()))
        entries += e
        return e
    }

    /**
     * Exercise 6. Check the chain. Walk it from the start and return the index of the first entry
     * whose `prev` is not the previous entry's hash (or [GENESIS] for entry 0), or whose `hash` is
     * not `sha256(prev, payload bytes)`. If every link holds but a [publishedHead] was given and
     * the chain's [head] differs from it, return [size]: the chain is consistent with itself but
     * not with what was published. Return null if everything checks out.
     */
    fun verify(publishedHead: ByteArray? = null): Int? {
        var expectedPrev = GENESIS
        for (e in entries) {
            if (!e.prev.contentEquals(expectedPrev)) return e.index                          // a broken link
            if (!e.hash.contentEquals(sha256(e.prev, e.payload.toByteArray()))) return e.index // edited payload
            expectedPrev = e.hash
        }
        if (publishedHead != null && !head.contentEquals(publishedHead)) return size         // rewritten or cut short
        return null
    }

    // Three ways to attack the log (finished), for the tests and demos.

    /** Edits one payload in place and leaves every hash alone: a careless edit. */
    fun tamper(index: Int, payload: String) {
        val old = entries[index]
        entries[index] = Entry(index, payload, old.prev, old.hash)
    }

    /** Edits one payload and recomputes every hash after it: an insider who controls the whole log. */
    fun rewriteFrom(index: Int, payload: String) {
        val tail = entries.subList(index, entries.size).map { it.payload }.toMutableList()
        tail[0] = payload
        while (entries.size > index) entries.removeAt(entries.size - 1)
        for (p in tail) append(p)
    }

    /** Drops the newest entries, keeping the first [keep]. */
    fun truncate(keep: Int) {
        while (entries.size > keep) entries.removeAt(entries.size - 1)
    }

    companion object {
        val GENESIS = ByteArray(32)
    }
}
