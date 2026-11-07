package sfz.internals.l03

import java.nio.ByteBuffer

class Frame(val index: Int) {
    val data: ByteBuffer = ByteBuffer.allocate(PAGE_SIZE)
    var pageId: Int = NO_PAGE
    var pinCount: Int = 0
    var dirty: Boolean = false
    var usageCount: Int = 0

    companion object {
        const val NO_PAGE = -1
    }
}

class NoFreeFrameException : IllegalStateException("no unpinned frame is available")

class BufferPool(private val disk: DiskManager, val capacity: Int) {
    private val frames = Array(capacity) { Frame(it) }
    private val pageTable = HashMap<Int, Frame>()
    private val free = ArrayDeque(frames.toList())
    private var hand = 0

    fun fetch(pageId: Int): Frame {
        pageTable[pageId]?.let { f ->
            // hit: no I/O at all, just one more pin and one more tick of usage
            f.pinCount++
            f.usageCount = minOf(f.usageCount + 1, MAX_USAGE)
            return f
        }
        val f = victim()                       // may throw NoFreeFrameException; nothing has changed yet
        evict(f)
        try {
            disk.readPage(pageId, f.data)
        } catch (e: Exception) {
            free.addFirst(f)                   // the frame is empty now; don't lose it
            throw e
        }
        load(f, pageId)
        return f
    }

    fun newPage(): Frame {
        val f = victim()                       // before allocatePage(), so a full pool does not leak a page id
        evict(f)
        val pageId = disk.allocatePage()
        f.data.clear()
        java.util.Arrays.fill(f.data.array(), 0.toByte())   // the frame may still hold another page's bytes
        load(f, pageId)
        f.dirty = true                         // the page exists only in memory until it is written
        return f
    }

    fun unpin(pageId: Int, dirty: Boolean) {
        val f = pageTable[pageId] ?: throw IllegalStateException("page $pageId is not in the pool")
        check(f.pinCount > 0) { "page $pageId is not pinned" }
        f.pinCount--
        if (dirty) f.dirty = true              // sticky: a later clean unpin must not lose an earlier change
    }

    fun flushAll() {
        for (f in pageTable.values) {
            if (f.dirty) {
                disk.writePage(f.pageId, f.data)
                f.dirty = false
            }
        }
    }

    fun cachedPages(): Set<Int> = pageTable.keys.toSet()

    private fun victim(): Frame {
        free.removeFirstOrNull()?.let { return it }
        var tries = capacity                   // PostgreSQL's trycounter
        while (true) {
            val f = frames[hand]
            hand = (hand + 1) % capacity       // the hand always moves on, so it rests just past the victim
            if (f.pinCount == 0) {
                if (f.usageCount == 0) return f
                f.usageCount--                 // second chance: survive this pass, but with one less credit
                tries = capacity
            } else if (--tries == 0) {
                throw NoFreeFrameException()   // a full lap of pinned frames: nothing can ever come free here
            }
        }
    }

    /** Empties [f]: writes its page back if dirty and removes it from the page table. */
    private fun evict(f: Frame) {
        if (f.pageId == Frame.NO_PAGE) return
        if (f.dirty) disk.writePage(f.pageId, f.data)   // write-back happens here, exactly once per eviction
        pageTable.remove(f.pageId)
        f.pageId = Frame.NO_PAGE
        f.dirty = false
    }

    private fun load(f: Frame, pageId: Int) {
        f.pageId = pageId
        f.pinCount = 1
        f.usageCount = 1
        f.dirty = false
        pageTable[pageId] = f
    }

    companion object {
        const val MAX_USAGE = 5
    }
}
