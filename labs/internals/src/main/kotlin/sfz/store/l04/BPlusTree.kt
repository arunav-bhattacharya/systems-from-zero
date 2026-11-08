package sfz.store.l04

/**
 * One node of the tree. In a database each node is one page (8 KB in PostgreSQL) and a pointer to a
 * node is a page number. Here the "pages" live in a list inside [BPlusTree], and a pointer is the
 * node's index in that list.
 */
sealed class Node {
    /** The node's keys, always in increasing order. */
    val keys = ArrayList<Long>()
}

/** A leaf: keys with their values, in key order, plus the page id of the next leaf to the right. */
class Leaf : Node() {
    val values = ArrayList<String>()

    /** The leaf to the right of this one, or [BPlusTree.NO_PAGE] for the rightmost leaf. */
    var next: Int = BPlusTree.NO_PAGE
}

/**
 * An internal node: `n` separator keys and `n + 1` children (page ids).
 * Child `i` holds the keys `k` with `keys[i - 1] <= k < keys[i]`: everything left of a separator is
 * smaller than it, everything right of it is greater or equal.
 */
class Internal : Node() {
    val children = ArrayList<Int>()
}

/**
 * A B+tree from `Long` keys to `String` values, held in memory.
 *
 * Order 4 (the default) means a node has at most 4 children, so at most 3 keys. Leaves hold the values
 * and are linked left to right; internal nodes hold only separator keys and child pointers.
 *
 * - A leaf that reaches `order` keys splits: the upper half moves to a new leaf on its right, and the new
 *   leaf's first key is COPIED up into the parent as the separator.
 * - An internal node that reaches `order` keys splits: the upper half moves to a new node, and the middle
 *   key is PUSHED up into the parent (it stays in neither half).
 * - When the root splits, a new root with one key is made above it. That is the only way the tree grows
 *   taller, so every leaf is always at the same depth.
 *
 * Your job: write [get], [put], [range] and the three private helpers [insert], [splitLeaf] and
 * [splitInternal]. Storage ([read], [allocate]), [childIndex], [levels] and [checkInvariants] are done:
 * read [checkInvariants] first, it is the list of rules your tree must keep.
 */
class BPlusTree(val order: Int = 4) {
    init {
        require(order >= 3) { "order must be at least 3, was $order" }
    }

    /** A node holds at most this many keys. */
    val maxKeys: Int get() = order - 1

    /** Every node except the root holds at least this many keys: ceil(order / 2) - 1. */
    val minKeys: Int get() = (order + 1) / 2 - 1

    private val pages = ArrayList<Node>()          // page id -> node: a stand-in for the index file

    /** Page id of the root node. */
    var root: Int = allocate(Leaf())
        private set

    /** Number of levels: 1 while the root is a leaf. */
    var height: Int = 1
        private set

    /** Number of keys in the tree. */
    var size: Int = 0
        private set

    /** How many nodes [read] has fetched: the page reads a disk-based tree would do. */
    var pageReads: Long = 0
        private set

    fun resetPageReads() {
        pageReads = 0
    }

    /** How many pages (nodes) the tree uses. */
    val pageCount: Int get() = pages.size

    /** The value for [key], or null. Reads exactly one node per level. */
    fun get(key: Long): String? {
        TODO("start at the root; while the node is Internal, follow children[childIndex(keys, key)]; then binary-search the leaf")
    }

    /** Inserts [key], or replaces its value if it is already there. */
    fun put(key: Long, value: String) {
        TODO("call insert(root, ...); if it returns a Split, make a new Internal root above the old root and the new node, and add 1 to height")
    }

    /** Every key in `[lo, hi]` with its value, in key order. Descends once, then follows the leaf chain. */
    fun range(lo: Long, hi: Long): List<Pair<Long, String>> {
        TODO("descend to the leaf where lo belongs, then walk keys and leaf.next until a key is > hi")
    }

    /** What a split hands to the parent: the separator key and the page id of the new right node. */
    private class Split(val separator: Long, val right: Int)

    /**
     * Inserts into the subtree rooted at [pageId]. Returns null if the subtree absorbed the key, or the
     * [Split] the parent must add if the node at [pageId] split.
     */
    private fun insert(pageId: Int, key: Long, value: String): Split? {
        TODO("leaf: insert in order (or replace), split if over maxKeys; internal: recurse into the child, add the child's Split, split if over maxKeys")
    }

    /** Moves the upper half of [leaf] to a new right sibling and returns its first key as the separator. */
    private fun splitLeaf(leaf: Leaf): Split {
        TODO("move keys and values from size/2 on into a new Leaf, link it into the chain, return Split(right's first key, right's page id)")
    }

    /** Moves the upper half of [node] to a new right sibling and pushes the middle key up. */
    private fun splitInternal(node: Internal): Split {
        TODO("keys[size/2] goes up; keys and children to its right move to a new Internal; return Split(that key, new page id)")
    }

    // ------------------------------------------------------------------ provided: storage, checks, debugging

    /** Fetches a node by page id and counts it. Follow every pointer through this method. */
    private fun read(pageId: Int): Node {
        pageReads++
        return pages[pageId]
    }

    /** Stores a new node and returns its page id. */
    private fun allocate(node: Node): Int {
        pages += node
        return pages.size - 1
    }

    /** The keys of every node, level by level from the root, each level left to right. Does not count reads. */
    fun levels(): List<List<List<Long>>> {
        val out = ArrayList<List<List<Long>>>()
        var level = listOf(root)
        while (level.isNotEmpty()) {
            out += level.map { pages[it].keys.toList() }
            level = level.flatMap { (pages[it] as? Internal)?.children ?: emptyList() }
        }
        return out
    }

    /**
     * Throws [IllegalStateException] if the tree breaks a B+tree rule. This is the definition of a valid
     * tree, in code:
     * 1. every leaf is at depth [height];
     * 2. keys are strictly increasing inside every node;
     * 3. every node holds at most [maxKeys] keys, and every node but the root at least [minKeys];
     *    an internal root holds at least one key;
     * 4. an internal node with n keys has n + 1 children;
     * 5. every key lies inside the bounds its ancestors' separators allow: `lo <= key < hi`;
     * 6. following `next` from the leftmost leaf visits every leaf once, left to right, and yields all
     *    [size] keys in increasing order.
     */
    fun checkInvariants() {
        val leavesInOrder = ArrayList<Int>()
        fun walk(id: Int, depth: Int, lo: Long?, hi: Long?) {
            val n = pages[id]
            val where = "page $id (depth $depth, keys ${n.keys})"
            check(n.keys.zipWithNext().all { (a, b) -> a < b }) { "$where: keys are not strictly increasing" }
            check(n.keys.size <= maxKeys) { "$where: more than $maxKeys keys" }
            if (id != root) check(n.keys.size >= minKeys) { "$where: fewer than $minKeys keys" }
            for (k in n.keys) {
                check(lo == null || k >= lo) { "$where: key $k is below its lower bound $lo" }
                check(hi == null || k < hi) { "$where: key $k is not below its upper bound $hi" }
            }
            when (n) {
                is Leaf -> {
                    check(depth == height) { "$where: leaf at depth $depth, but the tree has height $height" }
                    check(n.values.size == n.keys.size) { "$where: ${n.keys.size} keys but ${n.values.size} values" }
                    leavesInOrder += id
                }
                is Internal -> {
                    check(n.keys.isNotEmpty()) { "$where: an internal node needs at least one key" }
                    check(n.children.size == n.keys.size + 1) { "$where: ${n.keys.size} keys but ${n.children.size} children" }
                    for ((i, c) in n.children.withIndex()) {
                        walk(c, depth + 1, if (i == 0) lo else n.keys[i - 1], if (i == n.keys.size) hi else n.keys[i])
                    }
                }
            }
        }
        walk(root, 1, null, null)
        val chain = ArrayList<Int>()
        var at = leavesInOrder.first()
        while (at != NO_PAGE) {
            check(chain.size <= leavesInOrder.size) { "the leaf chain loops" }
            chain += at
            at = (pages[at] as Leaf).next
        }
        check(chain == leavesInOrder) { "the leaf chain $chain does not match the leaves left to right $leavesInOrder" }
        val all = chain.flatMap { pages[it].keys }
        check(all.size == size) { "the leaves hold ${all.size} keys but size is $size" }
        check(all.zipWithNext().all { (a, b) -> a < b }) { "keys along the leaf chain are not increasing" }
    }

    companion object {
        const val NO_PAGE = -1

        /**
         * Which child of an internal node to follow for [key]: the number of separators `<= key`.
         * With separators [30, 50], keys below 30 go to child 0, 30 to 49 to child 1, and 50 or more to child 2.
         */
        fun childIndex(keys: List<Long>, key: Long): Int {
            var lo = 0
            var hi = keys.size
            while (lo < hi) {                      // binary search for the first separator > key
                val mid = (lo + hi) ushr 1
                if (keys[mid] <= key) lo = mid + 1 else hi = mid
            }
            return lo
        }
    }
}
