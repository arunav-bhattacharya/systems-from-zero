package sfz.internals.l05

import sfz.internals.l01.ChannelFactory
import java.io.Closeable
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.file.Path

/** What one SSTable knows about a key. */
sealed interface Lookup {
    /** The table holds a value for the key. */
    class Value(val bytes: ByteArray) : Lookup

    /** The table holds a tombstone: the key was deleted, so older tables must not be asked. */
    data object Tombstone : Lookup

    /** The table knows nothing about the key: ask the next older table. */
    data object Missing : Lookup
}

/**
 * A sorted string table: an immutable file of records in key order, a sparse index and a Bloom filter.
 *
 * ```
 * data    records in key order:  [klen int][key bytes][vlen int][value bytes]   vlen = -1 is a tombstone
 * index   [count int], then per block: [klen int][key bytes][offset long]       one entry per 16 records
 * filter  BloomFilter.toBytes()
 * footer  [indexAt long][filterAt long][records int][MAGIC int]                 the last 24 bytes
 * ```
 *
 * A block is 16 records in a row. The index holds the first key of every block and where the block
 * starts, so it is 16 times smaller than the data. [open] reads the footer, the index and the filter
 * into memory, as RocksDB does when it opens a table file. After that a [get] costs at most one read.
 *
 * Your job: write [get]. Writing, opening, [blockFor] and [entries] are done.
 */
class SSTable private constructor(
    val path: Path,
    private val channel: FileChannel,
    /** The first key of each block, in order. */
    val indexKeys: List<String>,
    /** Where each block starts in the file. */
    private val indexOffsets: LongArray,
    /** Where the data ends (the index starts). */
    private val dataEnd: Long,
    val filter: BloomFilter,
    /** How many records (values and tombstones) the table holds. */
    val records: Int,
    /** The file's size in bytes. */
    val size: Long,
) : Closeable {

    /**
     * Looks [key] up with at most one read of the file:
     * 1. if the Bloom filter says no, the key is [Lookup.Missing] (no read);
     * 2. find the last block whose first key is `<= key` (none: [Lookup.Missing], no read);
     * 3. read that block, from its offset up to the next block's offset (or [dataEnd]), in ONE read,
     *    and scan its records for the key.
     */
    fun get(key: String): Lookup {
        TODO("filter says no: Missing. blockFor(key) < 0: Missing. Else read [indexOffsets[b], next offset or dataEnd) in one read and scan it")
    }

    /** Index of the last block whose first key is `<= key`, or -1. Binary search over [indexKeys]. */
    private fun blockFor(key: String): Int {
        var lo = 0
        var hi = indexKeys.size - 1
        var found = -1
        while (lo <= hi) {
            val mid = (lo + hi) ushr 1
            if (indexKeys[mid] <= key) {
                found = mid
                lo = mid + 1
            } else {
                hi = mid - 1
            }
        }
        return found
    }

    // ---------------------------------------------------------------- provided

    /** Every record in key order, a null value for a tombstone. Reads the whole data section in one read. */
    fun entries(): List<Pair<String, ByteArray?>> {
        val buf = ByteBuffer.allocate(dataEnd.toInt())
        readFully(buf, 0)
        buf.flip()
        val out = ArrayList<Pair<String, ByteArray?>>(records)
        while (buf.hasRemaining()) {
            val k = ByteArray(buf.getInt()).also { buf.get(it) }.decodeToString()
            val vlen = buf.getInt()
            out += k to (if (vlen == TOMBSTONE) null else ByteArray(vlen).also { buf.get(it) })
        }
        return out
    }

    private fun readFully(dst: ByteBuffer, pos: Long) {
        var at = pos
        while (dst.hasRemaining()) {
            val n = channel.read(dst, at)
            check(n >= 0) { "unexpected end of $path at $at" }
            at += n
        }
    }

    override fun close() = channel.close()

    companion object {
        const val TOMBSTONE = -1
        const val BLOCK_RECORDS = 16
        const val BITS_PER_KEY = 10
        const val FOOTER_SIZE = 24
        const val MAGIC = 0x55a7ab1e

        /**
         * Writes [entries] (already in key order; a null value is a tombstone) to a new file at [path],
         * forces it, and opens it. This is a memtable flush or a compaction's output.
         */
        fun write(
            path: Path,
            entries: Collection<Map.Entry<String, ByteArray?>>,
            channels: ChannelFactory = ChannelFactory.DEFAULT,
            bitsPerKey: Int = BITS_PER_KEY,
        ): SSTable {
            val data = java.io.ByteArrayOutputStream()
            val index = java.io.ByteArrayOutputStream()
            val filter = BloomFilter.forKeys(entries.size, bitsPerKey)
            var blocks = 0
            var prev: String? = null
            for ((i, e) in entries.withIndex()) {
                require(prev == null || prev < e.key) { "entries must be in strictly increasing key order: $prev, ${e.key}" }
                prev = e.key
                val k = e.key.encodeToByteArray()
                if (i % BLOCK_RECORDS == 0) {                           // a new block starts: index its first key
                    index.write(ByteBuffer.allocate(12 + k.size).putInt(k.size).put(k).putLong(data.size().toLong()).array())
                    blocks++
                }
                val v = e.value
                data.write(ByteBuffer.allocate(8 + k.size + (v?.size ?: 0)).putInt(k.size).put(k).putInt(v?.size ?: TOMBSTONE)
                    .apply { if (v != null) put(v) }.array())
                filter.add(e.key)                                       // tombstones go in the filter too
            }
            val indexAt = data.size().toLong()
            val filterBytes = filter.toBytes()
            val filterAt = indexAt + 4 + index.size()
            val file = ByteBuffer.allocate((filterAt + filterBytes.size + FOOTER_SIZE).toInt())
            file.put(data.toByteArray()).putInt(blocks).put(index.toByteArray()).put(filterBytes)
            file.putLong(indexAt).putLong(filterAt).putInt(entries.size).putInt(MAGIC)
            file.flip()
            channels.open(path).use { ch ->
                var at = 0L
                while (file.hasRemaining()) at += ch.write(file, at)
                ch.force(false)                                         // the table is durable before anyone relies on it
            }
            return open(path, channels)
        }

        /** Opens a table file: reads its footer, sparse index and Bloom filter into memory. */
        fun open(path: Path, channels: ChannelFactory = ChannelFactory.DEFAULT): SSTable {
            val ch = channels.open(path)
            val size = ch.size()
            val footer = ByteBuffer.allocate(FOOTER_SIZE)
            ch.read(footer, size - FOOTER_SIZE)
            footer.flip()
            val indexAt = footer.getLong()
            val filterAt = footer.getLong()
            val records = footer.getInt()
            check(footer.getInt() == MAGIC) { "$path is not an SSTable" }
            val meta = ByteBuffer.allocate((size - FOOTER_SIZE - indexAt).toInt())
            var at = indexAt
            while (meta.hasRemaining()) at += ch.read(meta, at)
            meta.flip()
            val blocks = meta.getInt()
            val keys = ArrayList<String>(blocks)
            val offsets = LongArray(blocks)
            for (b in 0 until blocks) {
                keys += ByteArray(meta.getInt()).also { meta.get(it) }.decodeToString()
                offsets[b] = meta.getLong()
            }
            val filterBytes = ByteArray((size - FOOTER_SIZE - filterAt).toInt())
            meta.position((filterAt - indexAt).toInt())
            meta.get(filterBytes)
            return SSTable(path, ch, keys, offsets, indexAt, BloomFilter.fromBytes(filterBytes), records, size)
        }
    }
}
