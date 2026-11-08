package sfz.batch.l02

/** Thrown when one more distinct key would not fit in the counter's memory budget. */
class MemoryBudgetExceeded(val distinctKeys: Int, val bytesNeeded: Long, val budgetBytes: Long) :
    RuntimeException("$distinctKeys distinct keys use the whole budget: the next one needs $bytesNeeded of $budgetBytes bytes")

/**
 * Counts keys in a hash map in one pass, like `awk '{n[$7]++}'` or a Kotlin `HashMap<String, Long>`,
 * but with a memory budget, so you can see where the approach stops working.
 *
 * Memory follows the number of distinct keys, not the number of lines. Each new key costs
 * [entryBytes]: a round [ENTRY_OVERHEAD_BYTES] for the map entry, the String object, the boxed Long
 * and the slot in the table on a 64-bit JVM, plus the key's own bytes. A key seen before costs nothing.
 */
class HashCounter(val budgetBytes: Long) {
    private val counts = HashMap<String, Long>()

    /** Bytes charged so far: the sum of [entryBytes] over the distinct keys. */
    var bytesUsed: Long = 0
        private set

    val distinctKeys: Int get() = counts.size

    /**
     * Adds one occurrence of [key]. A key already in the map just gets its count raised. A new key
     * is charged [entryBytes]; if that would take [bytesUsed] past [budgetBytes], throws
     * [MemoryBudgetExceeded] and leaves the counter as it was.
     */
    fun add(key: String) {
        val seen = counts[key]
        if (seen != null) {                                  // a repeat: no new memory
            counts[key] = seen + 1
            return
        }
        val cost = entryBytes(key)
        if (bytesUsed + cost > budgetBytes) throw MemoryBudgetExceeded(counts.size, bytesUsed + cost, budgetBytes)
        bytesUsed += cost                                    // a new key: one more entry, held to the end
        counts[key] = 1
    }

    /** Finished. The counts so far (a read-only view). */
    fun counts(): Map<String, Long> = counts

    companion object {
        const val ENTRY_OVERHEAD_BYTES = 100L

        fun entryBytes(key: String): Long = ENTRY_OVERHEAD_BYTES + key.toByteArray(Charsets.UTF_8).size
    }
}
