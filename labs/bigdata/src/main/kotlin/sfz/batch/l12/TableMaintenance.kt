package sfz.batch.l12

import org.apache.spark.sql.SparkSession

/** What a maintenance job looks at before deciding to compact. */
data class TableHealth(
    /** Snapshots still in the table's metadata (each one keeps its files alive). */
    val snapshots: Int,
    /** Data files in the current snapshot. */
    val dataFiles: Int,
    /** Delete files (position deletes, equality deletes or deletion vectors) in the current snapshot. */
    val deleteFiles: Int,
    /** Data files in the current snapshot smaller than the threshold passed to [TableMaintenance.health]. */
    val smallDataFiles: Int,
)

/** The counts `rewrite_data_files` reports. */
data class Compaction(val rewrittenDataFiles: Int, val addedDataFiles: Int, val removedDeleteFiles: Int)

/**
 * Housekeeping for one Iceberg table, done through Iceberg's Spark procedures
 * (`CALL <catalog>.system.<procedure>(...)`). [name] has three parts, `catalog.namespace.table`;
 * the procedures take the catalog in front of `system` and the rest as `table => 'namespace.table'`.
 */
class TableMaintenance(private val spark: SparkSession, val name: String) {

    /**
     * Counts what the current snapshot holds, using the metadata tables `<name>.data_files`,
     * `<name>.delete_files` (both have `file_size_in_bytes`) and `<name>.snapshots`.
     * A data file is small if it has fewer than [smallFileBytes] bytes.
     */
    fun health(smallFileBytes: Long = 64L * 1024 * 1024): TableHealth {
        TODO("count rows of the data_files, delete_files and snapshots metadata tables")
    }

    /**
     * Compacts the table with `rewrite_data_files`. Pass options so that it rewrites any group
     * of 2 or more small files (`min-input-files`), rewrites any file that has at least one
     * delete file attached (`delete-file-threshold`), and drops delete files that no longer
     * apply to any live data file (`remove-dangling-deletes`). Returns the counts from the
     * procedure's result row.
     */
    fun compact(): Compaction {
        TODO("CALL <catalog>.system.rewrite_data_files(table => ..., options => map(...))")
    }

    /**
     * Expires every snapshot except the newest [retainLast], with `expire_snapshots`
     * (`older_than` = now, `retain_last`), which also deletes the files that only the expired
     * snapshots used. Returns `deleted_data_files_count` from the result row.
     */
    fun expireSnapshots(retainLast: Int): Long {
        TODO("CALL <catalog>.system.expire_snapshots(table => ..., older_than => TIMESTAMP '...', retain_last => ...)")
    }
}
