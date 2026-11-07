package sfz.internals.support

import java.io.RandomAccessFile
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardOpenOption.APPEND

/**
 * File tricks that stand in for a crash. A process that dies in the middle of a write leaves a file
 * that ends early (a torn tail) or holds bytes that never formed a whole record.
 */
object Crash {
    /** Cuts the last [bytes] bytes off [file], as if the power failed before they reached the disk. */
    fun chopTail(file: Path, bytes: Long) {
        RandomAccessFile(file.toFile(), "rw").use { it.setLength(maxOf(0L, it.length() - bytes)) }
    }

    /** Flips every bit of the byte at [offset], as if that sector came back damaged. */
    fun flipByte(file: Path, offset: Long) {
        RandomAccessFile(file.toFile(), "rw").use {
            it.seek(offset)
            val b = it.read()
            it.seek(offset)
            it.write(b xor 0xFF)
        }
    }

    /** Appends raw [bytes] to [file], as if a write had started and left junk behind. */
    fun appendJunk(file: Path, bytes: ByteArray) {
        Files.write(file, bytes, APPEND)
    }
}
