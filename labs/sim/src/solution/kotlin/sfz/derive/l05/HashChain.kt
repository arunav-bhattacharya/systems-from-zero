package sfz.derive.l05

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
