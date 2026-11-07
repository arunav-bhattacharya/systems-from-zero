package sfz.bigdata.l09

import com.fasterxml.jackson.databind.ObjectMapper
import org.apache.avro.file.DataFileReader
import org.apache.avro.generic.GenericDatumReader
import org.apache.avro.generic.GenericRecord
import java.io.File

/** A snapshot as the table metadata file records it. */
data class SnapshotRef(val id: Long, val manifestList: String)

/**
 * Walks an Iceberg table's metadata tree by hand, from the files on disk, the way an engine does
 * before it reads a single row. The table lives in a Hadoop catalog, so its folder holds `data/`
 * and `metadata/`.
 *
 * Jackson (`com.fasterxml.jackson.databind.ObjectMapper`) and Avro
 * (`org.apache.avro.file.DataFileReader`) come with Spark, so both are on your classpath.
 */
object MetadataWalk {

    /**
     * The table's current metadata file. A Hadoop catalog writes `metadata/v1.metadata.json`,
     * `v2.metadata.json`, ... and keeps the number of the current one in
     * `metadata/version-hint.text`.
     */
    fun currentMetadataFile(tableDir: File): File {
        // the "pointer": one small file naming the current version
        val version = File(tableDir, "metadata/version-hint.text").readText().trim().toInt()
        return File(tableDir, "metadata/v$version.metadata.json")
    }

    /**
     * The current snapshot recorded in [metadataFile]: `current-snapshot-id`, and the
     * `manifest-list` of the entry in `snapshots` with that `snapshot-id`. Null if the table has no
     * snapshot yet (the id is -1).
     */
    fun currentSnapshot(metadataFile: File): SnapshotRef? {
        val json = ObjectMapper().readTree(metadataFile)
        val current = json.path("current-snapshot-id").asLong(-1)
        if (current == -1L) return null                       // created, never written to
        // every snapshot ever kept is listed; the current one is just the one the id names
        val snapshot = json.path("snapshots").first { it.path("snapshot-id").asLong() == current }
        return SnapshotRef(current, snapshot.path("manifest-list").asText())
    }

    /**
     * Every live data file of a snapshot, sorted, as paths. The manifest list is an Avro file with
     * one record per manifest (field `manifest_path`). Each manifest is an Avro file with one record
     * per data file: `status` (0 existing, 1 added, 2 deleted) and `data_file`, a record whose
     * `file_path` is the Parquet file. Skip deleted entries. Paths may start with `file:`; drop it.
     */
    fun dataFiles(manifestList: String): List<String> =
        // level 2: the manifest list names the manifests of this snapshot
        records(manifestList).map { it.get("manifest_path").toString() }
            // level 3: each manifest names data files, with their partition values and column stats
            .flatMap { manifest -> records(manifest) }
            .filter { (it.get("status") as Int) != 2 }
            .map { (it.get("data_file") as GenericRecord).get("file_path").toString().removePrefix("file:") }
            .sorted()

    private fun records(path: String): List<GenericRecord> =
        DataFileReader(File(path.removePrefix("file:")), GenericDatumReader<GenericRecord>()).use { it.toList() }
}
