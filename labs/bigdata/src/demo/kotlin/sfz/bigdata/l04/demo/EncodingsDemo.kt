package sfz.bigdata.l04.demo

import java.io.File
import java.sql.DriverManager

/**
 * One row group of 100,352 payments, written several ways. For each column it prints the encoding
 * DuckDB chose and the bytes the column chunk takes in the file.
 */
fun main() {
    val file = File("build/l04/encodings.parquet").apply { parentFile.mkdirs() }
    DriverManager.getConnection("jdbc:duckdb:").use { c ->
        c.createStatement().use { s ->
            s.execute("""CREATE TABLE p AS
                SELECT i AS payment_id,
                       ['AUTHORIZED','CAPTURED','DECLINED','REFUNDED'][(hash(i + 2) % 4)::INTEGER + 1] AS status,
                       (hash(i + 3) % 250000 + 100)::BIGINT AS amount_cents
                FROM range(100352) t(i)""")
        }
        fun show(label: String, column: String, order: String, options: String) {
            c.createStatement().use { it.execute("COPY (SELECT * FROM p ORDER BY $order) TO '${file.absolutePath}' (FORMAT parquet, $options)") }
            val (encoding, bytes) = c.rows("SELECT encodings, total_compressed_size FROM parquet_metadata('${file.absolutePath}') WHERE path_in_schema = '$column'").single()
            println("  %-36s %-20s %,10d bytes".format(label, encoding, bytes!!.toLong()))
        }
        val raw = "COMPRESSION uncompressed"
        println("status: 4 distinct values")
        show("strings, no dictionary", "status", "payment_id", "$raw, DICTIONARY_SIZE_LIMIT 1")
        show("dictionary + 2-bit codes", "status", "payment_id", raw)
        show("dictionary, rows sorted by status", "status", "status, payment_id", raw)
        println("payment_id: 0, 1, 2, 3, ...")
        show("8-byte values", "payment_id", "payment_id", raw)
        show("deltas (Parquet v2)", "payment_id", "payment_id", "$raw, PARQUET_VERSION V2")
        println("amount_cents: random")
        show("8-byte values", "amount_cents", "payment_id", raw)
        show("deltas (Parquet v2)", "amount_cents", "payment_id", "$raw, PARQUET_VERSION V2")
        show("8-byte values, then Snappy", "amount_cents", "payment_id", "COMPRESSION snappy")
        show("8-byte values, then Zstd", "amount_cents", "payment_id", "COMPRESSION zstd")
    }
}
