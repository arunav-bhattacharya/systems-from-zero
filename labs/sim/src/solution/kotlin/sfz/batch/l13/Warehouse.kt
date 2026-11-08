package sfz.batch.l13

import java.time.LocalDate

/**
 * Lesson batch-13 (given): a toy warehouse of tables partitioned by day. Each partition holds a list
 * of numbers. Read it, but you don't need to change it.
 *
 * [append] adds rows to a partition, the way `INSERT INTO` does. [overwrite] replaces a partition's
 * rows in one step, the way `INSERT OVERWRITE ... PARTITION (dt = ...)` or one table-format commit
 * does: a reader sees the old rows or the new rows, never a mix.
 */
class Warehouse {
    private val tables = mutableMapOf<String, MutableMap<LocalDate, List<Long>>>()

    fun read(table: String, day: LocalDate): List<Long> = tables[table]?.get(day) ?: emptyList()

    fun append(table: String, day: LocalDate, rows: List<Long>) {
        val t = tables.getOrPut(table) { sortedMapOf() }
        t[day] = (t[day] ?: emptyList()) + rows
    }

    fun overwrite(table: String, day: LocalDate, rows: List<Long>) {
        tables.getOrPut(table) { sortedMapOf() }[day] = rows.toList()
    }

    /** The days that have a partition in [table], oldest first. */
    fun partitions(table: String): List<LocalDate> = tables[table]?.keys?.sorted() ?: emptyList()

    /** The sum of every row of [table]. */
    fun total(table: String): Long = tables[table]?.values?.sumOf { it.sum() } ?: 0
}
