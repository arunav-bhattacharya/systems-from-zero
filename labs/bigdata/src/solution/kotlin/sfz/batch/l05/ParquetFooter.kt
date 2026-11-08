package sfz.batch.l05

import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.fs.Path
import org.apache.parquet.hadoop.ParquetFileReader
import org.apache.parquet.hadoop.util.HadoopInputFile
import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import org.apache.spark.sql.SaveMode
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** What a Parquet footer says about one column chunk: where its bytes are, and its smallest and largest value. */
data class ColumnChunk(
    val column: String,
    /** Byte offset in the file where the chunk starts. */
    val offset: Long,
    /** Bytes the chunk takes in the file, after encoding and compression. */
    val bytes: Long,
    /** Smallest value in the chunk, for whole-number columns. Null when the footer has no usable statistics. */
    val min: Long?,
    /** Largest value in the chunk, or null, like [min]. */
    val max: Long?,
)

/** One row group: a slice of the table's rows, stored as one chunk per column. */
data class RowGroup(val index: Int, val rows: Long, val columns: Map<String, ColumnChunk>)

object ParquetFooter {

    /**
     * The length in bytes of the footer of the Parquet file [file], read by hand.
     *
     * A Parquet file starts with the 4 bytes `PAR1` and ends with: the footer, then a 4-byte
     * little-endian integer holding the footer's length, then `PAR1` again. Read the last 8 bytes
     * with a `RandomAccessFile` and decode the integer. Throw `IllegalArgumentException` if the file
     * is shorter than 12 bytes or either magic number is missing.
     */
    fun footerLength(file: File): Int {
        RandomAccessFile(file, "r").use { f ->
            require(f.length() >= 12) { "$file is too short to be a Parquet file" }
            val head = ByteArray(4).also { f.readFully(it) }
            // the last 8 bytes: 4 bytes of footer length, then the magic number again
            f.seek(f.length() - 8)
            val tail = ByteArray(8).also { f.readFully(it) }
            require(String(head, Charsets.US_ASCII) == "PAR1" && String(tail, 4, 4, Charsets.US_ASCII) == "PAR1") {
                "$file does not start and end with PAR1"
            }
            // little-endian: the lowest byte comes first, so 0b 09 00 00 is 0x090b = 2,315
            return ByteBuffer.wrap(tail, 0, 4).order(ByteOrder.LITTLE_ENDIAN).int
        }
    }

    /**
     * Already written for you: decodes the footer of [file] with parquet-java (the library Spark
     * uses) and returns its row groups. Read it once to see what a footer holds.
     */
    fun read(file: File): List<RowGroup> =
        ParquetFileReader.open(HadoopInputFile.fromPath(Path(file.toURI()), Configuration())).use { reader ->
            reader.footer.blocks.mapIndexed { i, block ->
                val chunks = block.columns.associate { c ->
                    val name = c.path.toDotString()
                    val stats = c.statistics
                    // min/max as Long for INT32 and INT64 columns; strings and INT96 timestamps give null here
                    val lo = stats?.takeIf { it.hasNonNullValue() }?.genericGetMin() as? Number
                    val hi = stats?.takeIf { it.hasNonNullValue() }?.genericGetMax() as? Number
                    name to ColumnChunk(name, c.startingPos, c.totalSize, lo?.toLong(), hi?.toLong())
                }
                RowGroup(i, block.rowCount, chunks)
            }
        }
}

/** The decisions a Parquet reader makes from the footer, before it reads any data. */
object RowGroupSkipper {

    /**
     * Could [chunk] hold a value between [lo] and [hi] (both inclusive)? Only its min and max are
     * known. If the chunk has no statistics, the reader can't rule anything out.
     */
    fun mayContain(chunk: ColumnChunk, lo: Long, hi: Long): Boolean {
        val min = chunk.min ?: return true          // no statistics: the reader has to look
        val max = chunk.max ?: return true
        // the chunk's values all sit in min..max; they can match only if the two ranges overlap
        return max >= lo && min <= hi
    }

    /**
     * The indexes of the row groups a reader must read for `WHERE column BETWEEN lo AND hi`, in
     * file order. Every other row group can be skipped without reading it.
     */
    fun rowGroupsToRead(groups: List<RowGroup>, column: String, lo: Long, hi: Long): List<Int> {
        return groups.filter { g ->
            val chunk = g.columns[column] ?: throw IllegalArgumentException("no column '$column'")
            mayContain(chunk, lo, hi)
        }.map { it.index }
    }

    /**
     * The bytes a reader fetches when it reads only [columns] from only the row groups in [keep]:
     * the sum of the sizes of those column chunks. Everything else in the file stays on disk.
     */
    fun bytesToRead(groups: List<RowGroup>, keep: List<Int>, columns: Set<String>): Long {
        // column pruning (only `columns`) times row group skipping (only `keep`)
        return groups.filter { it.index in keep }
            .sumOf { g -> columns.sumOf { c -> g.columns[c]?.bytes ?: throw IllegalArgumentException("no column '$c'") } }
    }
}

/** Writing a file so that its statistics are useful. */
object SortedWriter {

    /**
     * Writes [payments] under the directory [dir] as ONE Parquet file whose rows are sorted by
     * [column], with row groups of about [rowGroupBytes] bytes (parquet-java's `parquet.block.size`
     * option). Replaces whatever is in [dir].
     */
    fun write(payments: Dataset<Row>, column: String, dir: String, rowGroupBytes: Long) {
        payments
            .repartition(1)                          // one task, so one output file
            .sortWithinPartitions(column)            // neighbouring rows have neighbouring values
            .write().mode(SaveMode.Overwrite)
            // small row groups, so even a test-sized file has several; parquet-java's default is 128 MB
            .option("parquet.block.size", rowGroupBytes)
            .parquet(dir)
    }
}
