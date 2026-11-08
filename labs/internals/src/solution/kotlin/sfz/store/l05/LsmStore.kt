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
        memtable[key] = value
        val n = key.length + value.size
        memtableBytes += n
        bytesPut += n
        if (memtableBytes >= memtableLimit) flush()
    }

    /** Deletes [key] by storing a tombstone in the memtable. Older tables may still hold the key. */
    fun delete(key: String) {
        memtable[key] = null                                  // a tombstone: "deleted as of now"
        memtableBytes += key.length
        bytesPut += key.length
        if (memtableBytes >= memtableLimit) flush()
    }

    /** The newest value of [key]: memtable first, then tables newest to oldest. Null if absent or deleted. */
    fun get(key: String): ByteArray? {
        if (memtable.containsKey(key)) return memtable[key]   // null here means a tombstone
        for (t in tables) {                                   // newest first
            when (val r = t.get(key)) {
                is Lookup.Value -> return r.bytes
                Lookup.Tombstone -> return null               // deleted: older tables must not answer
                Lookup.Missing -> continue
            }
        }
        return null
    }

    /** Writes the memtable to a new SSTable, makes it the newest table, and empties the memtable. */
    fun flush() {
        if (memtable.isEmpty()) return
        val t = SSTable.write(dir.resolve(fileName(nextSeq++)), memtable.entries, channels)
        tables.add(0, t)                                      // the newest table goes first
        bytesWritten += t.size
        memtable.clear()
        memtableBytes = 0
    }

    /**
     * Merges every SSTable into one. For each key the newest version wins. Tombstones are dropped, which is
     * safe only because no older table is left that could still hold the key. The memtable is not touched.
     */
    fun compact() {
        if (tables.isEmpty()) return
        val merged = TreeMap<String, ByteArray?>()
        for (t in tables.asReversed()) {                      // oldest first, so newer versions overwrite older ones
            for ((k, v) in t.entries()) merged[k] = v
        }
        val live = TreeMap<String, ByteArray?>()
        for ((k, v) in merged) if (v != null) live[k] = v     // drop tombstones and the values they hid
        val old = tables.toList()
        tables.clear()
        if (live.isNotEmpty()) {
            val t = SSTable.write(dir.resolve(fileName(nextSeq++)), live.entries, channels)
            bytesWritten += t.size                            // compaction writes every live byte again
            tables += t
        }
        for (t in old) {                                      // only now remove the inputs
            t.close()
            Files.delete(t.path)
        }
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
