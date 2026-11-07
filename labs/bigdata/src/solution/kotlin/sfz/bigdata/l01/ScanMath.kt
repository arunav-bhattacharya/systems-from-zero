package sfz.bigdata.l01

/** Disk and network vendors count in decimal: 1 MB is 1,000,000 bytes. */
const val MB: Long = 1_000_000L
const val GB: Long = 1_000L * MB
const val TB: Long = 1_000L * GB

/** HDFS and Spark size blocks in binary units: 128 MiB is 134,217,728 bytes. */
const val MiB: Long = 1L shl 20

enum class Layout { ROW, COLUMNAR }

data class Column(val name: String, val bytesPerValue: Int)

data class Table(
    val rows: Long,
    val columns: List<Column>,
    val layout: Layout,
    val compressionRatio: Double = 1.0,
)

object ScanMath {

    // time = bytes / bandwidth; everything else in this file is a variation of this line
    fun scanSeconds(bytes: Long, bytesPerSecond: Long): Double = bytes.toDouble() / bytesPerSecond

    // ceiling division in Longs: a 1-byte tail is still a block someone has to read
    fun blockCount(bytes: Long, blockSize: Long): Long = (bytes + blockSize - 1) / blockSize

    fun clusterSeconds(
        bytes: Long,
        blockSize: Long,
        bytesPerSecond: Long,
        machines: Int,
        startupSeconds: Double = 0.0,
    ): Double {
        val blocks = blockCount(bytes, blockSize)
        // the scheduler deals blocks out like cards: the busiest machine gets the rounded-up share
        val busiestBlocks = (blocks + machines - 1) / machines
        // a tiny file is one short block, so never charge more bytes than the file has
        val busiestBytes = minOf(bytes, busiestBlocks * blockSize)
        // machines run in parallel, so the job takes as long as its slowest member, plus startup once
        return startupSeconds + scanSeconds(busiestBytes, bytesPerSecond)
    }

    fun bytesRead(table: Table, columnsNeeded: Set<String>): Long {
        val byName = table.columns.associateBy { it.name }
        val unknown = columnsNeeded - byName.keys
        require(unknown.isEmpty()) { "no such column(s): $unknown" }
        val bytesPerRow = when (table.layout) {
            // a row layout drags every column through the disk, needed or not
            Layout.ROW -> table.columns.sumOf { it.bytesPerValue.toLong() }
            // a columnar layout skips the column chunks the query never mentions
            Layout.COLUMNAR -> columnsNeeded.sumOf { byName.getValue(it).bytesPerValue.toLong() }
        }
        return Math.round(table.rows.toDouble() * bytesPerRow / table.compressionRatio)
    }

    fun machinesNeeded(bytes: Long, blockSize: Long, bytesPerSecond: Long, targetSeconds: Double): Int? {
        val blocks = blockCount(bytes, blockSize)
        // more machines than blocks can't help: the extra machines have nothing to read
        for (m in 1..maxOf(1L, blocks).toInt()) {
            if (clusterSeconds(bytes, blockSize, bytesPerSecond, m) <= targetSeconds) return m
        }
        return null
    }
}
