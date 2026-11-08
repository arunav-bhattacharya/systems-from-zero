package sfz.store.l03

import java.nio.ByteBuffer

/**
 * One slot of buffer pool memory. It holds a copy of one disk page (or nothing, when [pageId] is [NO_PAGE]).
 * Callers read and change [data]. Only the [BufferPool] should change the other fields.
 */
class Frame(val index: Int) {
    /** The page's bytes while it is in this frame. */
    val data: ByteBuffer = ByteBuffer.allocate(PAGE_SIZE)

    /** Which disk page the frame holds, or [NO_PAGE]. */
    var pageId: Int = NO_PAGE

    /** How many callers are using the page right now. A frame with pins can never be evicted. */
    var pinCount: Int = 0

    /** True if [data] differs from the page on disk, so it must be written back before the frame is reused. */
    var dirty: Boolean = false

    /** CLOCK usage count: 1 when loaded, +1 per fetch up to [BufferPool.MAX_USAGE], -1 each time the hand passes. */
    var usageCount: Int = 0

    companion object {
        const val NO_PAGE = -1
    }
}

/** Thrown when a page must come in but every frame is pinned. */
class NoFreeFrameException : IllegalStateException("no unpinned frame is available")

/**
 * A buffer pool with [capacity] frames, using PostgreSQL's clock-sweep to choose a victim.
 *
 * - The page table maps a page id to the frame that holds it.
 * - [fetch] and [newPage] pin the page; the caller must [unpin] it once per pin.
 * - Free frames are used first, in index order. When none is left, the clock hand sweeps the frames:
 *   it skips pinned frames, takes the first unpinned frame whose usage count is 0, and decrements the
 *   usage count of every other unpinned frame it passes. The hand stops just after the frame it picked.
 * - A dirty victim is written to disk before its frame is reused. A clean one is just dropped.
 *
 * Your job: write [fetch], [newPage], [unpin], [flushAll] and [victim].
 */
class BufferPool(private val disk: DiskManager, val capacity: Int) {
    private val frames = Array(capacity) { Frame(it) }
    private val pageTable = HashMap<Int, Frame>()
    private val free = ArrayDeque(frames.toList())    // frames that hold no page yet
    private var hand = 0                               // the clock hand: index of the next frame to look at

    /**
     * Returns the frame holding [pageId], pinned once more.
     * - Hit: no disk I/O. Pin it and raise its usage count by one (up to [MAX_USAGE]).
     * - Miss: get a frame from [victim], write the old page back if it is dirty, read [pageId] from disk,
     *   then the frame holds the page with pin count 1, usage count 1, not dirty.
     * Throws [NoFreeFrameException] when every frame is pinned.
     */
    fun fetch(pageId: Int): Frame {
        TODO("hit: pin and bump usage; miss: victim, write back if dirty, read the page, update the page table")
    }

    /** Allocates a new page on disk and returns its frame: zeroed, pinned once, usage count 1, and dirty. */
    fun newPage(): Frame {
        TODO("get a victim frame FIRST, then disk.allocatePage(), zero the data, pin it, mark it dirty")
    }

    /** Drops one pin on [pageId]. `dirty = true` marks the page dirty; `dirty = false` never clears it. Throws [IllegalStateException] if it is not pinned. */
    fun unpin(pageId: Int, dirty: Boolean) {
        TODO("one pin less; dirty is sticky")
    }

    /** Writes every dirty page in the pool to disk once, and marks it clean. */
    fun flushAll() {
        TODO("write back dirty pages, clear their dirty flag")
    }

    /** The page ids in the pool right now. */
    fun cachedPages(): Set<Int> = pageTable.keys.toSet()

    /**
     * A frame to load a page into: a free frame if there is one, otherwise the clock-sweep victim.
     * Like PostgreSQL, give up with [NoFreeFrameException] after passing [capacity] pinned frames in a row
     * without decrementing any usage count.
     */
    private fun victim(): Frame {
        TODO("free list first; then sweep: skip pinned, take usage 0, otherwise decrement and move on")
    }

    companion object {
        /** PostgreSQL caps the usage count at 5 (BM_MAX_USAGE_COUNT). */
        const val MAX_USAGE = 5
    }
}
