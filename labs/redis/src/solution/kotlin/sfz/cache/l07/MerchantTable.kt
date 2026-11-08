package sfz.cache.l07

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

/**
 * The system of record for this lab: a merchants table in memory, standing in for Oracle. Done for you.
 *
 * Every [write] commits at once and adds one to the row's version, the way
 * `UPDATE merchants SET name = ?, version = version + 1` would. [reads] counts the queries, so a test
 * can see how many of them reached the "database".
 */
class MerchantTable {
    /** One committed row: the merchant's display name and its version. */
    data class Row(val name: String, val version: Long)

    private val rows = ConcurrentHashMap<String, Row>()
    private val readCount = AtomicInteger()

    /** How many times [read] has been called. */
    val reads: Int get() = readCount.get()

    /** The committed row for [id], or null if there is none. Counts as one query. */
    fun read(id: String): Row? {
        readCount.incrementAndGet()
        return rows[id]
    }

    /** Commits [name] for [id]: version 1 for a new row, the old version plus one otherwise. Returns the new row. */
    fun write(id: String, name: String): Row =
        rows.compute(id) { _, old -> Row(name, (old?.version ?: 0) + 1) }!!
}
