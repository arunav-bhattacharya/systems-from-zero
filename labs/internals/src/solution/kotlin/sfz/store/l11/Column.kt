package sfz.store.l11

// Lesson 11 lab, part 2: a column cut into chunks, each in its smallest encoding, with a zone map.
// Your job: ColumnChunk.of() and Column.countBetween(). Column.of() is done.

/** How many values a chunk holds by default. Parquet pages and DuckDB vectors are in this range too. */
const val CHUNK_ROWS = 2048

/**
 * Up to [CHUNK_ROWS] values of one column, stored in whichever encoding is smallest, plus its zone map:
 * the smallest and largest value in the chunk, [min] and [max]. The zone map is kept outside the encoded
 * data, so a scan can read it without decoding anything.
 */
class ColumnChunk(val encoded: Encoded, val min: Long, val max: Long) {
    val count: Int get() = encoded.count

    companion object {
        /**
         * Encodes [values] three ways ([RunLength], [BitPacked], [Plain]) and keeps the one with the fewest
         * [Encoded.sizeBytes] (on a tie, the first in that order), together with the min and max of [values].
         * [values] must not be empty.
         */
        fun of(values: LongArray): ColumnChunk {
            require(values.isNotEmpty()) { "a chunk holds at least one value" }
            val candidates = listOf(RunLength.encode(values), BitPacked.encode(values), Plain(values.copyOf()))
            val smallest = candidates.minBy { it.sizeBytes }          // minBy keeps the first of equal sizes
            return ColumnChunk(smallest, values.min(), values.max())
        }
    }
}

/**
 * One column of a table, stored as a list of chunks: what a column store keeps for each column. A query on
 * this column reads chunk by chunk, and [chunksDecoded] counts the chunks it had to decode.
 */
class Column(val chunks: List<ColumnChunk>) {
    var chunksDecoded = 0
        private set

    val count: Long get() = chunks.sumOf { it.count.toLong() }
    val sizeBytes: Long get() = chunks.sumOf { it.encoded.sizeBytes.toLong() }

    /**
     * How many values v have `lo <= v <= hi`, using each chunk's zone map first:
     * - the chunk's range [min, max] doesn't overlap [lo, hi]: skip it, nothing in it can match;
     * - it lies entirely inside [lo, hi]: every value matches, add its count without decoding;
     * - otherwise decode it (count it in [chunksDecoded]) and check each value.
     */
    fun countBetween(lo: Long, hi: Long): Long {
        var n = 0L
        for (c in chunks) {
            if (c.max < lo || c.min > hi) continue                       // zone map: no value can match
            if (lo <= c.min && c.max <= hi) { n += c.count; continue }   // zone map: every value matches
            chunksDecoded++                                              // only now touch the data
            for (v in c.encoded.decode()) if (v in lo..hi) n++
        }
        return n
    }

    companion object {
        /** Cuts [values] into chunks of [chunkRows] values, in order, and encodes each one. */
        fun of(values: LongArray, chunkRows: Int = CHUNK_ROWS): Column {
            require(chunkRows > 0) { "chunkRows must be positive" }
            val chunks = (values.indices step chunkRows).map { start ->
                ColumnChunk.of(values.copyOfRange(start, minOf(start + chunkRows, values.size)))
            }
            return Column(chunks)
        }
    }
}
