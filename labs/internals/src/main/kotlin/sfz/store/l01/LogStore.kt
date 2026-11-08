package sfz.store.l01

import java.io.Closeable
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.file.Path

/**
 * A Bitcask-style key-value store: one append-only file on disk, one hash map in memory.
 *
 * Every [put] and [delete] appends a [Record] to the end of `data.log`. The keydir (a [HashMap])
 * remembers, for each live key, where its newest value sits in the file, so [get] is one positional
 * read. On [open], the store rebuilds the keydir by scanning the file from the start.
 *
 * Your job: write [put], [get], [delete], [recover] and [merge]. The fields, [open], [close] and the
 * two I/O helpers at the bottom of this file are done.
 */
class LogStore private constructor(
    private val path: Path,
    private val channels: ChannelFactory,
) : Closeable {

    /** Where the newest value of one key sits in the file. */
    private class Entry(val valuePos: Long, val valueSize: Int)

    private var channel: FileChannel = channels.open(path)
    private val keydir = HashMap<String, Entry>()
    private var end = 0L                 // file offset where the next record goes

    /**
     * Appends a record for [key] and returns only when it is durable.
     * Write `Record.encode(key, value)` at [end], force the channel, then point the keydir at the value bytes
     * (they start `Record.HEADER_SIZE + key size in bytes` after the record) and move [end] past the record.
     */
    fun put(key: String, value: ByteArray) {
        TODO("append the record at `end`, force(), then update the keydir and `end`")
    }

    /** The newest value of [key], or null. Exactly one positional read; a missing key reads nothing. */
    fun get(key: String): ByteArray? {
        TODO("look the key up in the keydir, then read valueSize bytes at valuePos")
    }

    /** Deletes [key] durably: append a tombstone (`Record.encode(key, null)`), force, drop it from the keydir. */
    fun delete(key: String) {
        TODO("append a tombstone, force(), remove the key from the keydir")
    }

    /**
     * Rewrites the file so it holds one record per live key and nothing else.
     * Write the live records to a new file next to [path] (for example `data.log.merge`), force it,
     * close the old channel, move the new file over [path] with `Files.move(..., ATOMIC_MOVE, REPLACE_EXISTING)`,
     * reopen [channel] through [channels], and rebuild the keydir and [end] for the new offsets.
     */
    fun merge() {
        TODO("copy the live records to a new file, swap it in, rebuild the keydir")
    }

    override fun close() = channel.close()

    /**
     * Rebuilds the keydir from the file, the way a restart after a crash would.
     * Scan records from offset 0. Stop at the first record that is short (fewer bytes left than its header
     * or its sizes claim), has impossible sizes, or fails its CRC: that is a torn tail from a crash.
     * Truncate the file at that point so the next append lands right after the last good record. Set [end].
     */
    private fun recover() {
        TODO("scan, check each record's sizes and CRC, apply puts and tombstones, truncate the torn tail")
    }

    companion object {
        const val FILE_NAME = "data.log"

        /** Opens (or creates) the store in [dir] and recovers it. */
        fun open(dir: Path, channels: ChannelFactory = ChannelFactory.DEFAULT): LogStore =
            LogStore(dir.resolve(FILE_NAME), channels).also { it.recover() }
    }
}

/** Reads until [dst] is full, starting at file offset [pos]. One call to read() for any normal file. */
private fun FileChannel.readFully(dst: ByteBuffer, pos: Long) {
    var at = pos
    while (dst.hasRemaining()) {
        val n = read(dst, at)
        check(n >= 0) { "unexpected end of file at $at" }
        at += n
    }
}

/** Writes all of [src] starting at file offset [pos]. */
private fun FileChannel.writeFully(src: ByteBuffer, pos: Long) {
    var at = pos
    while (src.hasRemaining()) at += write(src, at)
}
