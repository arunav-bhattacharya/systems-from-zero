package sfz.bigdata.l09

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
        TODO("read version-hint.text and build the vN.metadata.json path")
    }

    /**
     * The current snapshot recorded in [metadataFile]: `current-snapshot-id`, and the
     * `manifest-list` of the entry in `snapshots` with that `snapshot-id`. Null if the table has no
     * snapshot yet (the id is -1).
     */
    fun currentSnapshot(metadataFile: File): SnapshotRef? {
        TODO("parse the JSON and find the current snapshot's manifest list")
    }

    /**
     * Every live data file of a snapshot, sorted, as paths. The manifest list is an Avro file with
     * one record per manifest (field `manifest_path`). Each manifest is an Avro file with one record
     * per data file: `status` (0 existing, 1 added, 2 deleted) and `data_file`, a record whose
     * `file_path` is the Parquet file. Skip deleted entries. Paths may start with `file:`; drop it.
     */
    fun dataFiles(manifestList: String): List<String> {
        TODO("read the manifest list, then every manifest it names")
    }
}
