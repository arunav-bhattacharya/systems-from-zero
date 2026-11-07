package sfz.bigdata.l04.demo

import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Reads the end of a Parquet file by hand, then prints the map of the file its footer holds. */
fun main() {
    PaymentParquet.open().use { c ->
        val file = PaymentParquet.sorted
        RandomAccessFile(file, "r").use { f ->
            val head = ByteArray(4).also { f.readFully(it) }
            f.seek(f.length() - 8)
            val tail = ByteArray(8).also { f.readFully(it) }
            val footerLength = ByteBuffer.wrap(tail, 0, 4).order(ByteOrder.LITTLE_ENDIAN).int
            println("file:          %s, %,d bytes".format(file.name, f.length()))
            println("first 4 bytes: %s".format(String(head)))
            println("last 8 bytes:  %s  (%s)".format(tail.joinToString(" ") { "%02x".format(it) }, String(tail, 4, 4)))
            println("footer:        %,d bytes, starting at byte %,d".format(footerLength, f.length() - 8 - footerLength))
        }
        // DuckDB decodes the footer for us: one row per column chunk
        val chunks = c.rows(
            """SELECT row_group_id, row_group_num_rows, path_in_schema, data_page_offset, dictionary_page_offset,
                      total_compressed_size, stats_min, stats_max
               FROM parquet_metadata('${file.absolutePath}') ORDER BY row_group_id, column_id""")
        for ((group, rows) in chunks.groupBy { it[0] }) {
            println("row group %s: %,d rows".format(group, rows[0][1]!!.toLong()))
            for (r in rows) {
                val start = minOf(r[3]!!.toLong(), r[4]?.toLong() ?: Long.MAX_VALUE)
                println("  %-13s at byte %,10d  %,8d bytes  min %-10s max %s".format(r[2], start, r[5]!!.toLong(), r[6], r[7]))
            }
            if (group == "1") { println("  ... row groups 2 and 3 look the same"); break }
        }
    }
}
