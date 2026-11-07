package sfz.internals.l01

import java.io.Closeable
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption.ATOMIC_MOVE
import java.nio.file.StandardCopyOption.REPLACE_EXISTING

class LogStore private constructor(
    private val path: Path,
    private val channels: ChannelFactory,
) : Closeable {

    private class Entry(val valuePos: Long, val valueSize: Int)

    private var channel: FileChannel = channels.open(path)
    private val keydir = HashMap<String, Entry>()
    private var end = 0L

    fun put(key: String, value: ByteArray) {
        val pos = append(Record.encode(key, value))
        // the value bytes start right after the header and the key
        keydir[key] = Entry(pos + Record.HEADER_SIZE + key.encodeToByteArray().size, value.size)
    }

    fun get(key: String): ByteArray? {
        val e = keydir[key] ?: return null           // a miss costs no I/O at all
        val buf = ByteBuffer.allocate(e.valueSize)
        channel.readFully(buf, e.valuePos)           // one positional read: the keydir knows exactly where to look
        return buf.array()
    }

    fun delete(key: String) {
        if (key !in keydir) return
        append(Record.encode(key, null))             // the tombstone must be durable before we forget the key
        keydir.remove(key)
    }

    fun merge() {
        val tmp = path.resolveSibling("$FILE_NAME.merge")
        Files.deleteIfExists(tmp)                    // left over from a crash during an earlier merge
        val fresh = HashMap<String, Entry>()
        var pos = 0L
        channels.open(tmp).use { out ->
            for ((key, e) in keydir) {
                val value = ByteArray(e.valueSize)
                channel.readFully(ByteBuffer.wrap(value), e.valuePos)
                val rec = Record.encode(key, value)
                val len = rec.remaining()
                out.writeFully(rec, pos)
                fresh[key] = Entry(pos + Record.HEADER_SIZE + key.encodeToByteArray().size, value.size)
                pos += len
            }
            out.force(true)                          // the new file must be on disk before it replaces the old one
        }
        channel.close()
        // rename is atomic: after a crash you find either the old file or the new one, never half of each.
        // A production store would also fsync the directory so the rename itself is durable.
        Files.move(tmp, path, ATOMIC_MOVE, REPLACE_EXISTING)
        channel = channels.open(path)
        keydir.clear()
        keydir.putAll(fresh)
        end = pos
    }

    override fun close() = channel.close()

    private fun recover() {
        val size = channel.size()
        val header = ByteBuffer.allocate(Record.HEADER_SIZE)
        var pos = 0L
        while (true) {
            // 1. is there a whole header left? A crash can cut the file anywhere, even inside the header
            if (size - pos < Record.HEADER_SIZE) break
            header.clear()
            channel.readFully(header, pos)
            val crc = header.getInt(Record.CRC_AT)
            val ksz = header.getInt(Record.KEY_SIZE_AT)
            val vsz = header.getInt(Record.VALUE_SIZE_AT)
            // 2. never trust sizes from a torn header: they can be any bytes at all
            if (ksz < 0 || vsz < Record.TOMBSTONE) break
            val len = Record.length(ksz, vsz)
            if (pos + len > size) break               // the record claims more bytes than the file has
            // 3. read the whole record and check the CRC before believing any of it
            val rec = ByteBuffer.allocate(len.toInt())
            channel.readFully(rec, pos)
            if (Record.crc(rec.array(), Record.TSTAMP_AT, rec.capacity() - Record.TSTAMP_AT) != crc) break
            // 4. apply it: later records win, a tombstone removes the key
            val key = String(rec.array(), Record.HEADER_SIZE, ksz, Charsets.UTF_8)
            if (vsz == Record.TOMBSTONE) keydir.remove(key)
            else keydir[key] = Entry(pos + Record.HEADER_SIZE + ksz, vsz)
            pos += len
        }
        // 5. cut off the torn tail. Without this, the next put lands after the garbage,
        //    and the NEXT recovery stops at the garbage and loses that put.
        if (pos < size) {
            channel.truncate(pos)
            channel.force(true)
        }
        end = pos
    }

    /** Writes [rec] at the end of the file, forces it to disk, and returns the offset it was written at. */
    private fun append(rec: ByteBuffer): Long {
        val pos = end
        val len = rec.remaining()
        channel.writeFully(rec, pos)
        channel.force(false)                          // fdatasync on Linux, F_FULLFSYNC on macOS: now it survives power loss
        end = pos + len
        return pos
    }

    companion object {
        const val FILE_NAME = "data.log"

        fun open(dir: Path, channels: ChannelFactory = ChannelFactory.DEFAULT): LogStore =
            LogStore(dir.resolve(FILE_NAME), channels).also { it.recover() }
    }
}

private fun FileChannel.readFully(dst: ByteBuffer, pos: Long) {
    var at = pos
    while (dst.hasRemaining()) {
        val n = read(dst, at)
        check(n >= 0) { "unexpected end of file at $at" }
        at += n
    }
}

private fun FileChannel.writeFully(src: ByteBuffer, pos: Long) {
    var at = pos
    while (src.hasRemaining()) at += write(src, at)
}
