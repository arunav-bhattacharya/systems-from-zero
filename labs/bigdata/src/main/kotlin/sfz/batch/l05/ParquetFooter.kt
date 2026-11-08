package sfz.batch.l05

import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.fs.Path
import org.apache.parquet.hadoop.ParquetFileReader
import org.apache.parquet.hadoop.util.HadoopInputFile
import org.apache.spark.sql.Dataset
import org.apache.spark.sql.Row
import java.io.File

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
        TODO("seek to length - 8, read 8 bytes, check PAR1 at both ends, decode a little-endian Int")
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
        TODO("compare the filter's range with the chunk's min and max")
    }

    /**
     * The indexes of the row groups a reader must read for `WHERE column BETWEEN lo AND hi`, in
     * file order. Every other row group can be skipped without reading it.
     */
    fun rowGroupsToRead(groups: List<RowGroup>, column: String, lo: Long, hi: Long): List<Int> {
        TODO("keep the row groups whose chunk of `column` may contain a match")
    }

    /**
     * The bytes a reader fetches when it reads only [columns] from only the row groups in [keep]:
     * the sum of the sizes of those column chunks. Everything else in the file stays on disk.
     */
    fun bytesToRead(groups: List<RowGroup>, keep: List<Int>, columns: Set<String>): Long {
        TODO("sum the chunk sizes of the needed columns in the kept row groups")
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
        TODO("one partition, sorted within it, written with the parquet.block.size option")
    }
}
