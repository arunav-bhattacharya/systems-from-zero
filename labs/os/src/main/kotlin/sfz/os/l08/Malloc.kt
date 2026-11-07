package sfz.os.l08

import java.util.BitSet
import java.util.TreeMap

/** glibc's sizes on 64-bit Linux. Written for you. */
object Sizes {
    const val PAGE = 4096L
    /** Bytes from the start of a chunk to the pointer malloc returns (the previous chunk's size field and this one's). */
    const val HEADER = 16L
    /** The smallest chunk glibc makes. */
    const val MIN_CHUNK = 32L
    /** A free chunk keeps its size and its list links in its first 48 bytes, so malloc_trim can't give those back. */
    const val FREE_HEADER = 48L
    /** Requests up to 32 MB that came from mmap raise the mmap threshold when they are freed. */
    const val MMAP_THRESHOLD_MAX = 32L shl 20

    /** The chunk glibc carves for a request of [n] bytes: n plus an 8-byte size field, rounded up to 16, at least 32. */
    fun chunkSize(n: Long): Long = maxOf(MIN_CHUNK, (n + 8 + 15) and 15L.inv())

    fun pageUp(x: Long): Long = (x + PAGE - 1) and (PAGE - 1).inv()
    fun pageDown(x: Long): Long = x and (PAGE - 1).inv()
}

/**
 * One arena's heap, modelled on glibc's malloc.
 *
 * Chunks sit end to end from [base]. After the last chunk comes the top chunk: free space up to the
 * program break, [brk], which malloc moves with the `brk` system call. Requests of [mmapThreshold]
 * or more that don't fit get their own `mmap`. Every system call is logged in [syscalls], in the
 * spirit of strace: `brk +135168`, `brk -192937984`, `mmap 208896`, `munmap 1052672`, `madvise 28672`.
 *
 * The program is assumed to write every byte it allocates, so a chunk's pages are resident from
 * the moment malloc hands it out. Pages leave RAM only when brk moves down, an mmap is unmapped,
 * or [trim] releases them.
 *
 * glibc finds free chunks through bins sorted by size and per-thread caches (tcache); this model
 * scans its free chunks in address order and takes the first that fits. The RSS story is the same.
 *
 * [trim] and the private helpers are written for you. Write [malloc] and [free].
 */
class Heap(val base: Long = 0x5555_0000_0000L) {
    /** Free chunks below the top chunk: start address -> size, in address order. */
    private val freeChunks = TreeMap<Long, Long>()
    /** Chunks in use on the heap: start address -> size. */
    private val used = HashMap<Long, Long>()
    private val mapped = HashMap<Long, Long>()               // pointer -> size of its own mmap
    private var nextMmap = base + (1L shl 36)                 // mmaps live far above the heap
    private val resident = BitSet()                          // heap pages in RAM, numbered from base

    var mmapThreshold = 128 * 1024L; private set
    var trimThreshold = 128 * 1024L; private set
    val topPad = 128 * 1024L

    /** Start of the top chunk: everything from here up to [brk] is free. */
    var top = base; private set
    /** The program break: the end of the heap. */
    var brk = base; private set

    val syscalls: MutableList<String> = mutableListOf()

    /** Bytes between [base] and [brk]: what `sbrk(0) - start` shows. */
    val heapBytes: Long get() = brk - base
    /** Bytes of this heap in RAM, plus every live mmap: this arena's share of RSS. */
    val rssBytes: Long get() = resident.cardinality() * Sizes.PAGE + mapped.values.sum()
    /** Free bytes malloc could hand out without a system call: free chunks plus the top chunk. */
    val freeBytes: Long get() = freeChunks.values.sum() + (brk - top)
    /** The biggest chunk that fits without a system call: the largest free chunk, or the top chunk minus its minimum. */
    val largestFree: Long get() = maxOf(freeChunks.values.maxOrNull() ?: 0L, brk - top - Sizes.MIN_CHUNK)
    /** Chunks in use, mmapped ones included. */
    val liveChunks: Int get() = used.size + mapped.size

    /**
     * malloc(n): the pointer to a block of at least [n] bytes.
     * 1. The first free chunk (lowest address) that holds [Sizes.chunkSize] bytes. Split off the rest
     *    as a new free chunk if it's at least MIN_CHUNK; otherwise hand out the whole free chunk.
     * 2. Otherwise the top chunk, if it holds the chunk plus MIN_CHUNK.
     * 3. Otherwise a chunk of [mmapThreshold] or more gets its own mapping ([mmapChunk]).
     * 4. Otherwise [grow] the heap with brk, and carve from the top.
     * Record the chunk in `used`, [touch] its pages, and return its start plus [Sizes.HEADER].
     */
    fun malloc(n: Long): Long {
        TODO("chunkSize(n); first fit in freeChunks (split when the rest is at least MIN_CHUNK); else the top chunk if it holds size + MIN_CHUNK; else mmapChunk for size >= mmapThreshold; else grow(size) and carve from top. Record it in used, touch its pages, return start + HEADER")
    }

    /**
     * free(ptr). An mmapped block is unmapped at once ([unmap]). A heap chunk becomes free and
     * merges with a free neighbour on either side. If it ends where the top chunk starts, it
     * becomes part of the top chunk, and a top chunk of [trimThreshold] or more is trimmed with
     * [shrink] (keeping [topPad]). Nothing else leaves RAM: a free chunk's pages stay resident.
     */
    fun free(ptr: Long) {
        TODO("mapped pointer: unmap. Else take the chunk out of used, merge with a free chunk that starts where it ends and one that ends where it starts; if the result ends at top, move top down and shrink(topPad) when brk - top >= trimThreshold, otherwise put it in freeChunks")
    }

    /**
     * malloc_trim(0): give back every whole page inside a free chunk (madvise MADV_DONTNEED; the
     * addresses stay in the heap, the RAM goes), then trim the top chunk down to almost nothing.
     * Returns the bytes released. Written for you.
     */
    fun trim(): Long {
        var released = 0L
        for ((start, size) in freeChunks) {
            val from = Sizes.pageUp(start + Sizes.FREE_HEADER)     // the chunk's links must stay
            val to = Sizes.pageDown(start + size)
            if (to <= from) continue
            resident.clear(page(from), page(to))
            released += to - from
        }
        if (released > 0) syscalls += "madvise $released"
        return released + shrink(0)
    }

    /** Lower the break so that at most [pad] bytes (plus a page) of top chunk stay. Returns the bytes released. */
    private fun shrink(pad: Long): Long {
        val area = brk - top - Sizes.MIN_CHUNK - 1
        if (area <= pad) return 0
        val extra = Sizes.pageDown(area - pad)
        if (extra == 0L) return 0
        brk -= extra
        resident.clear(page(brk), page(brk + extra))             // the kernel frees the pages above the break
        syscalls += "brk -$extra"
        return extra
    }

    /** Raise the break enough for a chunk of [size] at the top, plus [topPad] spare, in whole pages, as glibc does. */
    private fun grow(size: Long) {
        val extra = Sizes.pageUp(size + topPad + Sizes.MIN_CHUNK - (brk - top))
        brk += extra
        syscalls += "brk +$extra"
    }

    /** A chunk of [size] in a mapping of its own: the size plus 8 bytes, in whole pages. */
    private fun mmapChunk(size: Long): Long {
        val length = Sizes.pageUp(size + 8)
        val ptr = nextMmap + Sizes.HEADER
        nextMmap += length + Sizes.PAGE
        mapped[ptr] = length
        syscalls += "mmap $length"
        return ptr
    }

    /** munmap an mmapped block. Freeing one raises the mmap threshold to its size (up to 32 MB), as glibc does. */
    private fun unmap(ptr: Long) {
        val length = mapped.remove(ptr)!!
        syscalls += "munmap $length"
        if (length > mmapThreshold && length <= Sizes.MMAP_THRESHOLD_MAX) {
            mmapThreshold = length
            trimThreshold = 2 * length
        }
    }

    private fun page(address: Long): Int = ((address - base) / Sizes.PAGE).toInt()

    private fun touch(from: Long, to: Long) {
        resident.set(page(from), page(to - 1) + 1)
    }
}

/**
 * glibc's arenas: separate heaps, so threads don't all wait for one lock.
 *
 * Thread 0 is the main thread and uses the main arena, the brk heap. Any other thread gets an
 * arena at its first malloc: a new one while there are fewer than [limit], and after that an
 * existing one, taken round robin starting from the main arena. A thread keeps its arena.
 * A block always goes back to the arena it came from, whichever thread frees it.
 *
 * [newArena], [malloc] and [free] are written for you. Write [arenaFor].
 */
class Arenas(val cpus: Int, val arenaMax: Int = 0) {
    /** MALLOC_ARENA_MAX when set, otherwise glibc's default of 8 per CPU on 64-bit. */
    val limit: Int get() = if (arenaMax > 0) arenaMax else 8 * cpus

    val heaps: MutableList<Heap> = mutableListOf(Heap(MAIN_BASE))
    private val byThread = HashMap<Int, Heap>()
    private val owner = HashMap<Long, Heap>()
    private var nextShared = 0

    /** The arena [thread] allocates from, choosing one at its first call. */
    fun arenaFor(thread: Int): Heap {
        TODO("a thread keeps its arena; thread 0 uses heaps[0]; otherwise newArena() while heaps.size < limit, else heaps[nextShared++ % heaps.size]")
    }

    /** A new arena with its own heap, far from the others. Written for you. */
    private fun newArena(): Heap = Heap(ARENA_BASE + heaps.size * (1L shl 40)).also { heaps += it }

    fun malloc(thread: Int, n: Long): Long = arenaFor(thread).let { heap -> heap.malloc(n).also { owner[it] = heap } }

    fun free(ptr: Long) = owner.remove(ptr)!!.free(ptr)

    /** RSS of every arena together. */
    val rssBytes: Long get() = heaps.sumOf { it.rssBytes }

    /** Address space taken: the main heap up to its break, and 64 MB reserved up front for each other arena. */
    val reservedBytes: Long get() = heaps[0].heapBytes + (heaps.size - 1) * ARENA_RESERVE

    companion object {
        const val MAIN_BASE = 0x5555_0000_0000L
        const val ARENA_BASE = 0x7000_0000_0000L
        /** Each non-main arena reserves a 64 MB heap (2 x the 32 MB mmap threshold maximum). */
        const val ARENA_RESERVE = 64L shl 20
    }
}
