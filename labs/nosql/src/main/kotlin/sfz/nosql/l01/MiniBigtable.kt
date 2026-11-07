package sfz.nosql.l01

import java.util.TreeMap

/** One version of one cell: the [value] written to ([row], [column]) at [timestamp]. */
data class Cell(val row: String, val column: String, val timestamp: Long, val value: String)

/** A row as a read returns it: the newest value of every column the row has, ordered by column name. */
data class Row(val key: String, val columns: Map<String, String>)

/**
 * A tiny, single-machine Bigtable: ONE sorted map from (row, column, timestamp) to a value.
 *
 * The Bigtable paper (OSDI 2006) describes the data model as
 * `(row:string, column:string, time:int64) -> string`. Columns are named `family:qualifier`.
 * Families are declared when the table is created; qualifiers are free-form and can differ per row.
 * The map is sparse: a column that a row never wrote takes no space at all.
 *
 * Everything below works on [cells], kept in the order Bigtable keeps its data:
 * row ascending, then column ascending, then timestamp DESCENDING, so the newest version
 * of a cell is the first one you meet.
 *
 * @param families the column families this table allows, such as `setOf("pay", "risk")`
 * @param maxVersions how many versions of each cell to keep; older ones are dropped on write
 */
class MiniBigtable(families: Set<String>, private val maxVersions: Int = 3) {
    private val families: Set<String> = families.toSet()

    /** The whole table. Its order comes from [CellKey.compareTo]. */
    private val cells = TreeMap<CellKey, String>()

    /** The sort key of the map. */
    data class CellKey(val row: String, val column: String, val timestamp: Long) : Comparable<CellKey> {
        /** Row ascending, then column ascending, then timestamp descending (newest first). */
        override fun compareTo(other: CellKey): Int {
            TODO("compare row, then column, then timestamp in REVERSE")
        }
    }

    /**
     * Writes [value] to ([row], [column]) at [timestamp].
     *
     * - [column] must look like `family:qualifier` and its family must be one of the declared
     *   families. Otherwise throw [IllegalArgumentException].
     * - Writing the same (row, column, timestamp) again replaces that version.
     * - Afterwards keep only the [maxVersions] newest versions of this cell; remove the rest.
     */
    fun put(row: String, column: String, timestamp: Long, value: String) {
        TODO("validate the family, insert into cells, then drop versions beyond maxVersions")
    }

    /** All stored versions of one cell, newest first. Empty if the cell was never written. */
    fun versions(row: String, column: String): List<Cell> {
        TODO("walk cells from CellKey(row, column, Long.MAX_VALUE) while row and column still match")
    }

    /** The newest value of one cell, or null. Given: built on [versions]. */
    fun get(row: String, column: String): String? = versions(row, column).firstOrNull()?.value

    /**
     * The newest value of every column of [row]. Only columns the row actually has appear.
     * Careful: row `pay-1` must not pick up the cells of row `pay-10`.
     */
    fun readRow(row: String): Map<String, String> {
        TODO("walk cells from the first key of this row while the row still matches; keep the first (newest) value per column")
    }

    /**
     * Up to [limit] rows whose key starts with [prefix], in row-key order, each with the newest
     * value of each of its columns. This is a range read: start at the first possible key for
     * [prefix] and stop at the first row that no longer starts with it.
     */
    fun scan(prefix: String, limit: Int): List<Row> {
        TODO("walk cells from CellKey(prefix, \"\", Long.MAX_VALUE), group consecutive cells by row, stop at the prefix end or limit")
    }

    /** How many cell versions the table holds in total. Given. */
    fun cellCount(): Int = cells.size

    /** The family part of `family:qualifier`, or null if there is no colon. Given. */
    private fun familyOf(column: String): String? = column.substringBefore(':', missingDelimiterValue = "").ifEmpty { null }
}
