package sfz.store.l05

import sfz.store.l01.ChannelFactory
import java.io.Closeable
import java.nio.file.Files
import java.nio.file.Path
import java.util.TreeMap

/**
 * A small LSM tree: a sorted memtable in memory, and immutable SSTable files on disk.
 *
 * - [put] and [delete] only change the memtable (a delete stores a tombstone, a null value). When the
 *   memtable holds [memtableLimit] bytes or more, it is [flush]ed to a new SSTable.
 * - [get] asks the memtable first, then the tables from newest to oldest, and stops at the first one
 *   that knows the key. A tombstone means "deleted": stop and return null.
 * - [compact] merges every table into one, newest value per key, and drops the tombstones.
 *
 * There is no write-ahead log yet, so whatever is in the memtable is lost in a [crash]. Lesson 6 fixes that.
 *
 * Your job: write [put], [delete], [get], [flush] and [compact]. Opening, [close], [crash] and the
 * counters are done.
 */
class LsmStore private constructor(
    private val dir: Path,
    val memtableLimit: Int,
    private val channels: ChannelFactory,
) : Closeable {

    /** Key -> value, in key order. A null value is a tombstone. */
    private val memtable = TreeMap<String, ByteArray?>()

    /** Roughly how many bytes the memtable holds: key and value bytes of every entry put since the last flush. */
    private var memtableBytes = 0

    /** The SSTables, NEWEST FIRST. */
    private val tables = ArrayList<SSTable>()

    /** The number in the next SSTable's file name. A higher number is a newer table. */
    private var nextSeq = 1

    /** Bytes of keys and values the application asked to store. */
    var bytesPut: Long = 0
        private set

    /** Bytes written to SSTable files, by flushes and compactions. */
    var bytesWritten: Long = 0
        private set

    /** Bytes written to disk per byte put. */
    val writeAmplification: Double get() = if (bytesPut == 0L) 0.0 else bytesWritten.toDouble() / bytesPut

    /** Stores [value] for [key] in the memtable; flushes when the memtable reaches [memtableLimit] bytes. */
    fun put(key: String, value: ByteArray) {
        TODO("memtable[key] = value; add key.length + value.size to memtableBytes and bytesPut; flush() at memtableLimit")
    }

    /** Deletes [key] by storing a tombstone in the memtable. Older tables may still hold the key. */
    fun delete(key: String) {
        TODO("memtable[key] = null (a tombstone); count key.length; flush() at memtableLimit")
    }

    /** The newest value of [key]: memtable first, then tables newest to oldest. Null if absent or deleted. */
    fun get(key: String): ByteArray? {
        TODO("memtable.containsKey first (a null value is a tombstone), then each table newest first: Value, Tombstone or Missing")
    }

    /** Writes the memtable to a new SSTable, makes it the newest table, and empties the memtable. */
    fun flush() {
        TODO("skip if empty; SSTable.write(dir.resolve(fileName(nextSeq++)), memtable.entries, channels); add it FIRST in tables; count its size; clear")
    }

    /**
     * Merges every SSTable into one. For each key the newest version wins. Tombstones are dropped, which is
     * safe only because no older table is left that could still hold the key. The memtable is not touched.
     */
    fun compact() {
        TODO("merge tables oldest to newest into a TreeMap, drop tombstones, write one new table, then close and delete the old files")
    }

    // ---------------------------------------------------------------- provided

    /** The SSTables, newest first. */
    fun tables(): List<SSTable> = tables.toList()

    /** A clean shutdown: flush the memtable, close the files. */
    override fun close() {
        flush()
        tables.forEach { it.close() }
    }

    /** A crash: the process dies, the memtable is gone, the files stay as they are. */
    fun crash() {
        memtable.clear()
        tables.forEach { it.close() }
    }

    companion object {
        fun fileName(seq: Int) = "%06d.sst".format(seq)

        /** Opens the store in [dir], with every SSTable already there, newest first. */
        fun open(dir: Path, memtableLimit: Int = 64 * 1024, channels: ChannelFactory = ChannelFactory.DEFAULT): LsmStore {
            val store = LsmStore(dir, memtableLimit, channels)
            val files = Files.list(dir).use { s -> s.filter { it.fileName.toString().endsWith(".sst") }.toList() }
                .sortedByDescending { it.fileName.toString() }
            for (f in files) store.tables += SSTable.open(f, channels)
            store.nextSeq = (files.maxOfOrNull { it.fileName.toString().substringBefore(".").toInt() } ?: 0) + 1
            return store
        }
    }
}
