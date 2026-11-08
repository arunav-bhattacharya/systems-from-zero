package sfz.batch.l12

import org.apache.spark.sql.Row
import org.apache.spark.sql.SparkSession
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

data class TableHealth(
    val snapshots: Int,
    val dataFiles: Int,
    val deleteFiles: Int,
    val smallDataFiles: Int,
)

data class Compaction(val rewrittenDataFiles: Int, val addedDataFiles: Int, val removedDeleteFiles: Int)

class TableMaintenance(private val spark: SparkSession, val name: String) {
    // procedures live in the catalog: CALL l12.system.x(table => 'pay.t')
    private val catalog = name.substringBefore('.')
    private val table = name.substringAfter('.')

    fun health(smallFileBytes: Long = 64L * 1024 * 1024): TableHealth {
        // the metadata tables read the current snapshot's manifests, not the folder
        val sizes = spark.sql("SELECT file_size_in_bytes FROM $name.data_files").collectAsList().map { it.getLong(0) }
        return TableHealth(
            snapshots = count("SELECT count(*) FROM $name.snapshots"),
            dataFiles = sizes.size,
            deleteFiles = count("SELECT count(*) FROM $name.delete_files"),
            smallDataFiles = sizes.count { it < smallFileBytes },
        )
    }

    fun compact(): Compaction {
        // bin-pack: read small files and files with deletes, write fewer, bigger, clean files,
        // and commit them as one "replace" snapshot that holds the same rows
        val r = spark.sql(
            """
            CALL $catalog.system.rewrite_data_files(
                table => '$table',
                options => map(
                    'min-input-files', '2',
                    'delete-file-threshold', '1',
                    'remove-dangling-deletes', 'true'))
            """.trimIndent()
        ).first()
        return Compaction(r.int("rewritten_data_files_count"), r.int("added_data_files_count"), r.int("removed_delete_files_count"))
    }

    fun expireSnapshots(retainLast: Int): Long {
        // "now" in the session's time zone, because a TIMESTAMP literal is read in that zone
        val zone = ZoneId.of(spark.conf().get("spark.sql.session.timeZone"))
        val now = ZonedDateTime.now(zone).format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS"))
        // drops old snapshots from the metadata, then deletes every file no remaining snapshot lists
        val r = spark.sql(
            "CALL $catalog.system.expire_snapshots(table => '$table', older_than => TIMESTAMP '$now', retain_last => $retainLast)"
        ).first()
        return r.getAs<Long>("deleted_data_files_count")
    }

    private fun count(sql: String) = spark.sql(sql).first().getLong(0).toInt()

    private fun Row.int(field: String) = (getAs<Any>(field) as Number).toInt()
}
