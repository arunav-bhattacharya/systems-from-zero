package sfz.internals.l06

import sfz.internals.l01.ChannelFactory
import java.io.ByteArrayOutputStream
import java.io.Closeable
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption.ATOMIC_MOVE
import java.nio.file.StandardCopyOption.REPLACE_EXISTING
import java.util.zip.CRC32C

/** What a log record says happened. */
enum class RecordType(val code: Byte) {
    /** A transaction started. */
    BEGIN(1),

    /** A transaction set page [LogRecord.pageId] to [LogRecord.value] (the after-image). */
    UPDATE(2),

    /** A transaction committed: its updates must survive any crash from now on. */
    COMMIT(3),

    /** A transaction gave up: its updates must never be applied. */
    ABORT(4),

    /** A checkpoint finished. [LogRecord.value] is the redo LSN, [LogRecord.txId] the next transaction id. */
    CHECKPOINT(5),
}

/**
 * One log record. Every record is [SIZE] bytes on disk, so record n starts at byte n x 29:
 *
 * ```
 * offset  0      4      12     13     17       21
 *         | crc  | lsn  | type | txId | pageId | value |
 *           int    long   byte   int    int      long
 * ```
 *
 * The LSN (log sequence number) is the byte offset where the record starts in the log, as in PostgreSQL.
 * Storing it inside the record lets recovery check that a record is where it claims to be.
 * This file is complete: read it, don't change it.
 */
class LogRecord(val lsn: Long, val type: RecordType, val txId: Int, val pageId: Int, val value: Long) {
    /** The LSN just past this record: where the next record starts. */
    val endLsn: Long get() = lsn + SIZE

    fun encode(): ByteBuffer {
        val b = ByteBuffer.allocate(SIZE)
        b.putInt(0).putLong(lsn).put(type.code).putInt(txId).putInt(pageId).putLong(value)
        b.putInt(0, crc(b.array()))
        return b.flip()
    }

    override fun toString() = "$type(lsn=$lsn, tx=$txId, page=$pageId, value=$value)"

    companion object {
        const val SIZE = 29

        /** Decodes a record that should start at [expectedLsn], or returns null if it is damaged or torn. */
        fun decode(bytes: ByteArray, expectedLsn: Long): LogRecord? {
            if (bytes.size < SIZE) return null
            val b = ByteBuffer.wrap(bytes)
            if (b.getInt(0) != crc(bytes)) return null
            val lsn = b.getLong(4)
            val type = RecordType.entries.firstOrNull { it.code == b.get(12) } ?: return null
            if (lsn != expectedLsn) return null
            return LogRecord(lsn, type, b.getInt(13), b.getInt(17), b.getLong(21))
        }

        private fun crc(bytes: ByteArray): Int = CRC32C().run { update(bytes, 4, SIZE - 4); value.toInt() }
    }
}

/**
 * The write-ahead log: one append-only file plus an in-memory buffer of records not yet written.
 *
 * - [append] puts a record in the buffer (like PostgreSQL's WAL buffers) and gives it the next LSN.
 *   Nothing reaches the file yet, so a crash loses it.
 * - [flush] writes everything buffered to the file and forces it, if the log is not already durable
 *   up to the LSN asked for. One flush makes every earlier record durable, whoever appended it: that is
 *   group commit.
 * - [recover] reads the durable log from an LSN, stops at the first torn or damaged record and truncates
 *   the file there, exactly like lesson 1's store.
 *
 * This file is complete: read it, don't change it.
 */
class Wal(path: Path, channels: ChannelFactory) : Closeable {
    private val channel: FileChannel = channels.open(path)
    private val buffer = ByteArrayOutputStream()

    /** Every record that ends at or before this LSN is on disk and forced. */
    var flushedLsn: Long = channel.size()
        private set

    /** The LSN the next appended record gets. */
    var nextLsn: Long = flushedLsn
        private set

    /** Appends a record to the buffer and returns it, with its LSN. */
    fun append(type: RecordType, txId: Int, pageId: Int = -1, value: Long = 0): LogRecord {
        val rec = LogRecord(nextLsn, type, txId, pageId, value)
        buffer.write(rec.encode().array())
        nextLsn = rec.endLsn
        return rec
    }

    /** Makes the log durable at least up to [upTo]. Does no I/O at all if it already is. */
    fun flush(upTo: Long = nextLsn) {
        if (upTo <= flushedLsn) return
        val bytes = ByteBuffer.wrap(buffer.toByteArray())
        var at = flushedLsn
        while (bytes.hasRemaining()) at += channel.write(bytes, at)
        channel.force(false)
        buffer.reset()
        flushedLsn = at
    }

    /**
     * Reads the durable records from [from] onwards. Stops at the first record that is short, damaged
     * or not at the LSN it claims, truncates the file there, and makes that the end of the log.
     */
    fun recover(from: Long): List<LogRecord> {
        val size = channel.size()
        val out = ArrayList<LogRecord>()
        var at = from
        while (at + LogRecord.SIZE <= size) {
            val rec = LogRecord.decode(readBytes(at), at) ?: break
            out += rec
            at = rec.endLsn
        }
        if (at < size) {
            channel.truncate(at)                   // cut the torn or damaged tail off
            channel.force(true)
        }
        buffer.reset()
        flushedLsn = at
        nextLsn = at
        return out
    }

    /** The durable record at [lsn], or null if there is no valid one there. */
    fun readAt(lsn: Long): LogRecord? =
        if (lsn < 0 || lsn + LogRecord.SIZE > channel.size()) null else LogRecord.decode(readBytes(lsn), lsn)

    private fun readBytes(at: Long): ByteArray {
        val b = ByteBuffer.allocate(LogRecord.SIZE)
        var pos = at
        while (b.hasRemaining()) {
            val n = channel.read(b, pos)
            if (n < 0) break
            pos += n
        }
        return b.array()
    }

    /** The process dies: whatever is still in the buffer is gone. */
    fun crash() {
        buffer.reset()
        channel.close()
    }

    override fun close() = channel.close()
}

/**
 * A tiny file that remembers where the last checkpoint record is, like PostgreSQL's `global/pg_control`.
 * It is replaced atomically: write a temporary file, force it, rename it over the old one.
 * This file is complete: read it, don't change it.
 */
class ControlFile(private val path: Path) {
    /** The LSN of the last checkpoint record, or null if there has never been a checkpoint. */
    fun read(): Long? {
        if (!Files.exists(path)) return null
        val b = ByteBuffer.wrap(Files.readAllBytes(path))
        return if (b.remaining() == 8) b.getLong() else null
    }

    fun write(checkpointLsn: Long) {
        val tmp = path.resolveSibling(path.fileName.toString() + ".tmp")
        FileChannel.open(tmp, java.nio.file.StandardOpenOption.CREATE, java.nio.file.StandardOpenOption.WRITE,
            java.nio.file.StandardOpenOption.TRUNCATE_EXISTING).use { ch ->
            ch.write(ByteBuffer.allocate(8).putLong(checkpointLsn).flip())
            ch.force(true)
        }
        Files.move(tmp, path, ATOMIC_MOVE, REPLACE_EXISTING)
    }
}
