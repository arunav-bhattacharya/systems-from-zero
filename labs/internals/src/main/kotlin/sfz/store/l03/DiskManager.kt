package sfz.store.l03

import java.io.Closeable
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.file.Path
import java.nio.file.StandardOpenOption.CREATE
import java.nio.file.StandardOpenOption.READ
import java.nio.file.StandardOpenOption.WRITE

/** Size of one page, on disk and in a buffer pool frame. */
const val PAGE_SIZE = 4096

/**
 * Reads and writes whole pages by number. Page `n` lives at byte offset `n * PAGE_SIZE` of one file.
 * This file is complete: read it, don't change it.
 *
 * Both methods always move all [PAGE_SIZE] bytes of the buffer they are given, whatever its position and limit.
 */
interface DiskManager {
    /** Copies page [pageId] into [dst]. */
    fun readPage(pageId: Int, dst: ByteBuffer)

    /** Copies [src] over page [pageId] on disk. */
    fun writePage(pageId: Int, src: ByteBuffer)

    /** Reserves the next page number. The page reads as zeros until something writes it. */
    fun allocatePage(): Int
}

/** A [DiskManager] over a real file, using positional [FileChannel] reads and writes. */
class FileDiskManager(path: Path) : DiskManager, Closeable {
    private val channel = FileChannel.open(path, CREATE, READ, WRITE)
    private var pages = (channel.size() / PAGE_SIZE).toInt()

    /** How many pages the file holds, counting allocated pages not written yet. */
    val pageCount: Int get() = pages

    override fun readPage(pageId: Int, dst: ByteBuffer) {
        require(pageId in 0 until pages) { "page $pageId does not exist (the file has $pages pages)" }
        val b = dst.duplicate().clear()
        var pos = pageId.toLong() * PAGE_SIZE
        while (b.hasRemaining()) {
            val n = channel.read(b, pos)
            if (n < 0) break                 // allocated but never written: past the end of the file
            pos += n
        }
        while (b.hasRemaining()) b.put(0)
    }

    override fun writePage(pageId: Int, src: ByteBuffer) {
        require(pageId in 0 until pages) { "page $pageId was never allocated" }
        val b = src.duplicate().clear()
        var pos = pageId.toLong() * PAGE_SIZE
        while (b.hasRemaining()) pos += channel.write(b, pos)
    }

    override fun allocatePage(): Int = pages++

    /** fsync: makes every written page durable. */
    fun sync() = channel.force(false)

    override fun close() = channel.close()
}
