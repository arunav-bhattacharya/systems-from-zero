package sfz.bigdata.l01

/** Disk and network vendors count in decimal: 1 MB is 1,000,000 bytes. */
const val MB: Long = 1_000_000L
const val GB: Long = 1_000L * MB
const val TB: Long = 1_000L * GB

/** HDFS and Spark size blocks in binary units: 128 MiB is 134,217,728 bytes. */
const val MiB: Long = 1L shl 20

/** How a table stores its rows on disk. */
enum class Layout {
    /** Whole rows one after another (CSV, JSON lines, a heap table). A scan reads every column. */
    ROW,

    /** Each column stored on its own (Parquet, ORC). A scan reads only the columns it needs. */
    COLUMNAR,
}

/** A column and the bytes one value takes on disk before compression. */
data class Column(val name: String, val bytesPerValue: Int)

/**
 * A table's size and shape. [compressionRatio] is how many times smaller the stored bytes are than
 * the raw values: 4.0 means 4 raw bytes take 1 byte on disk.
 */
data class Table(
    val rows: Long,
    val columns: List<Column>,
    val layout: Layout,
    val compressionRatio: Double = 1.0,
)

/**
 * Back-of-the-envelope scan math. Every number here is "how long does reading take", because a
 * full scan of a big table spends almost all of its time moving bytes.
 *
 * Use decimal units for bandwidth ([MB], [GB]) and binary units for block sizes ([MiB]), the way
 * the real tools do.
 */
object ScanMath {

    /** Seconds for one reader to stream [bytes] at [bytesPerSecond]. */
    fun scanSeconds(bytes: Long, bytesPerSecond: Long): Double {
        TODO("bytes divided by bandwidth, as a Double")
    }

    /**
     * How many blocks a file of [bytes] splits into with [blockSize]-byte blocks.
     * The last block may be short, and it still counts. An empty file has 0 blocks.
     */
    fun blockCount(bytes: Long, blockSize: Long): Long {
        TODO("ceiling division without going through Double")
    }

    /**
     * Seconds for [machines] identical machines to scan [bytes], split into [blockSize] blocks.
     *
     * Each machine reads whole blocks at [bytesPerSecond]. The scheduler spreads the blocks as
     * evenly as it can, so the busiest machine gets ceil(blocks / machines) of them. The job ends
     * when the busiest machine finishes. [startupSeconds] is paid once, before any machine reads.
     *
     * Careful with tiny files: the busiest machine never reads more than [bytes] in total.
     */
    fun clusterSeconds(
        bytes: Long,
        blockSize: Long,
        bytesPerSecond: Long,
        machines: Int,
        startupSeconds: Double = 0.0,
    ): Double {
        TODO("startup + the busiest machine's bytes / bytesPerSecond")
    }

    /**
     * Bytes a query that needs [columnsNeeded] reads from [table], after compression.
     *
     * A [Layout.ROW] table reads whole rows whatever the query needs. A [Layout.COLUMNAR] table
     * reads only the needed columns. Either way, divide by the compression ratio and round to the
     * nearest byte. Throw [IllegalArgumentException] if a needed column is not in the table.
     */
    fun bytesRead(table: Table, columnsNeeded: Set<String>): Long {
        TODO("rows x bytes per row actually read / compressionRatio")
    }

    /**
     * The fewest machines that scan [bytes] within [targetSeconds] (no startup time), or null if
     * no number of machines can: even one block per machine takes too long.
     *
     * A loop over 1, 2, 3, ... machines using [clusterSeconds] is fine here.
     */
    fun machinesNeeded(bytes: Long, blockSize: Long, bytesPerSecond: Long, targetSeconds: Double): Int? {
        TODO("try more machines until the busiest one finishes in time; stop when every machine has one block")
    }
}
