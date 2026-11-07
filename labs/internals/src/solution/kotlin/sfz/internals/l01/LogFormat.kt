package sfz.internals.l01

import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.file.Path
import java.nio.file.StandardOpenOption.CREATE
import java.nio.file.StandardOpenOption.READ
import java.nio.file.StandardOpenOption.WRITE
import java.util.zip.CRC32C

/**
 * The on-disk layout of one record in the log. This file is complete: read it, don't change it.
 *
 * ```
 * offset  0      4          12     16     20
 *         | crc  | tstamp   | ksz  | vsz  | key bytes | value bytes |
 *           int    long       int    int
 * ```
 *
 * `crc` is a CRC-32C of every byte after it (tstamp to the end of the value).
 * `vsz` is [TOMBSTONE] (-1) for a delete, and then there are no value bytes.
 * This is the Bitcask entry format: crc, timestamp, key size, value size, key, value.
 */
object Record {
    const val HEADER_SIZE = 20
    const val TOMBSTONE = -1

    // where each header field starts, counted from the first byte of the record
    const val CRC_AT = 0
    const val TSTAMP_AT = 4
    const val KEY_SIZE_AT = 12
    const val VALUE_SIZE_AT = 16

    /** Encodes one record, ready to write: position 0, limit = record length. A null value encodes a tombstone. */
    fun encode(key: String, value: ByteArray?, tstamp: Long = System.currentTimeMillis()): ByteBuffer {
        val k = key.encodeToByteArray()
        val buf = ByteBuffer.allocate(HEADER_SIZE + k.size + (value?.size ?: 0))
        buf.putInt(0)                                   // crc, filled in below
        buf.putLong(tstamp)
        buf.putInt(k.size)
        buf.putInt(value?.size ?: TOMBSTONE)
        buf.put(k)
        if (value != null) buf.put(value)
        buf.putInt(CRC_AT, crc(buf.array(), TSTAMP_AT, buf.capacity() - TSTAMP_AT))
        return buf.flip()
    }

    /** CRC-32C of `len` bytes of [bytes] starting at [off]. */
    fun crc(bytes: ByteArray, off: Int, len: Int): Int {
        val c = CRC32C()
        c.update(bytes, off, len)
        return c.value.toInt()
    }

    /** Total length on disk of a record with these header sizes. */
    fun length(keySize: Int, valueSize: Int): Long = HEADER_SIZE.toLong() + keySize + maxOf(valueSize, 0)
}

/** Opens the store's file. The tests pass their own factory so they can count reads, writes and forces. */
fun interface ChannelFactory {
    fun open(path: Path): FileChannel

    companion object {
        val DEFAULT = ChannelFactory { FileChannel.open(it, CREATE, READ, WRITE) }
    }
}
