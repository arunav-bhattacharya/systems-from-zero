package sfz.internals.support

import java.nio.ByteBuffer
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import java.nio.channels.FileLock
import java.nio.channels.ReadableByteChannel
import java.nio.channels.WritableByteChannel
import java.nio.file.Path
import java.nio.file.StandardOpenOption.CREATE
import java.nio.file.StandardOpenOption.READ
import java.nio.file.StandardOpenOption.WRITE

/**
 * A [FileChannel] that counts what the code under test asks of the disk.
 *
 * Every read, write and force is counted and appended to [events] ("read", "write", "force"),
 * so a test can check both how many I/O calls happened and in what order.
 *
 * By default [force] is counted but NOT passed to the real file. The tests simulate crashes by
 * cutting and corrupting files, not by pulling the power, so a real fsync would only make them slow
 * (a few milliseconds each on a laptop SSD). Pass `realForce = true` to sync for real.
 */
class CountingFileChannel(
    private val delegate: FileChannel,
    private val realForce: Boolean = false,
) : FileChannel() {
    var reads = 0; private set
    var writes = 0; private set
    var forces = 0; private set
    val events = mutableListOf<String>()

    fun resetCounts() {
        reads = 0; writes = 0; forces = 0; events.clear()
    }

    private fun read() { reads++; events += "read" }
    private fun write() { writes++; events += "write" }

    override fun read(dst: ByteBuffer): Int { read(); return delegate.read(dst) }
    override fun read(dsts: Array<out ByteBuffer>, offset: Int, length: Int): Long { read(); return delegate.read(dsts, offset, length) }
    override fun read(dst: ByteBuffer, position: Long): Int { read(); return delegate.read(dst, position) }
    override fun write(src: ByteBuffer): Int { write(); return delegate.write(src) }
    override fun write(srcs: Array<out ByteBuffer>, offset: Int, length: Int): Long { write(); return delegate.write(srcs, offset, length) }
    override fun write(src: ByteBuffer, position: Long): Int { write(); return delegate.write(src, position) }

    override fun force(metaData: Boolean) {
        forces++
        events += "force"
        if (realForce) delegate.force(metaData)
    }

    override fun position(): Long = delegate.position()
    override fun position(newPosition: Long): FileChannel { delegate.position(newPosition); return this }
    override fun size(): Long = delegate.size()
    override fun truncate(size: Long): FileChannel { delegate.truncate(size); return this }
    override fun transferTo(position: Long, count: Long, target: WritableByteChannel): Long { read(); return delegate.transferTo(position, count, target) }
    override fun transferFrom(src: ReadableByteChannel, position: Long, count: Long): Long { write(); return delegate.transferFrom(src, position, count) }
    override fun map(mode: MapMode, position: Long, size: Long): MappedByteBuffer = delegate.map(mode, position, size)
    override fun lock(position: Long, size: Long, shared: Boolean): FileLock = delegate.lock(position, size, shared)
    override fun tryLock(position: Long, size: Long, shared: Boolean): FileLock? = delegate.tryLock(position, size, shared)
    override fun implCloseChannel() = delegate.close()

    companion object {
        /** Opens [path] for read and write (creating it) and wraps it. */
        fun open(path: Path, realForce: Boolean = false) =
            CountingFileChannel(FileChannel.open(path, CREATE, READ, WRITE), realForce)
    }
}
