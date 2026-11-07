package sfz.os.l06

/**
 * Address layout of arm64 Linux with 4 KB pages, the lab box's kernel (48-bit virtual addresses).
 * x86-64 with 4-level paging splits an address the same way: 9 + 9 + 9 + 9 bits of table index, 12 bits of offset.
 */
object Paging {
    const val PAGE_SHIFT = 12
    const val PAGE_SIZE = 1L shl PAGE_SHIFT        // 4096
    const val LEVELS = 4
    const val INDEX_BITS = 9
    const val ENTRIES = 1 shl INDEX_BITS          // 512 entries of 8 bytes: one table fills one 4 KB page

    /** The table index at each level, root (level 0) first, and the byte offset inside the page. */
    data class Split(val indices: List<Int>, val offset: Int)

    /** The virtual page number: the address without its 12 offset bits. Written for you. */
    fun pageNumber(va: Long): Long = va ushr PAGE_SHIFT

    /**
     * Cut [va] into four 9-bit indices and a 12-bit offset. Bits 47..39 index the root,
     * 38..30 level 1, 29..21 level 2, 20..12 level 3, and 11..0 are the offset.
     */
    fun split(va: Long): Split {
        TODO("shift right by 39, 30, 21 and 12 and keep 9 bits for each index; keep the low 12 bits for the offset")
    }
}

/** A range the program asked the kernel for (an mmap, the heap, a thread stack): one line of `/proc/<pid>/maps`. */
data class Region(val name: String, val start: Long, val size: Long) {
    operator fun contains(va: Long): Boolean = va >= start && va < start + size
}

/**
 * One process's page table: a tree of 512-entry tables. Entries at levels 0 to 2 point to the next
 * table down; entries at level 3 hold a physical frame number. A table exists only once something
 * under it is mapped, which is why 1 GB of mostly empty address space costs almost nothing.
 */
class PageTable {
    private class Table {
        val entries = arrayOfNulls<Any>(Paging.ENTRIES)    // Table at levels 0..2, Long (a frame) at level 3
    }

    private val root = Table()

    /** Tables in the tree, the root included. Each is one 4 KB page of memory: what VmPTE counts. */
    var tables = 1
        private set

    /** The frame [va]'s page is mapped to, or null when any level of the walk finds an empty entry. */
    fun lookup(va: Long): Long? {
        TODO("walk from root through levels 0 to 2 (null at the first empty entry), then read the frame at level 3")
    }

    /** Point [va]'s page at [frame], creating any missing tables on the way down. */
    fun map(va: Long, frame: Long) {
        TODO("walk like lookup, creating a Table (and counting it in tables) wherever an entry is empty; store frame at level 3")
    }
}

/** The translation lookaside buffer: the last [capacity] page translations, least recently used evicted first. */
class Tlb(val capacity: Int) {
    // TODO: keep the translations here. A LinkedHashMap with accessOrder = true and an overridden
    // removeEldestEntry is an LRU cache in five lines.

    val size: Int get() = TODO("how many translations the TLB holds now")

    /** The frame for virtual page [vpn], or null on a miss. A hit counts as a use. */
    fun lookup(vpn: Long): Long? {
        TODO("return the cached frame, and mark it as the most recently used")
    }

    /** Remember a translation, evicting the least recently used one when full. */
    fun insert(vpn: Long, frame: Long) {
        TODO("store it; when there are more than capacity entries, drop the least recently used")
    }
}

enum class Outcome { TLB_HIT, TLB_MISS, PAGE_FAULT, SEGFAULT }

/**
 * The hardware's address translation with the kernel's page-fault handler behind it.
 * Demand paging: no page has a frame until the first access to it.
 */
class Mmu(private val regions: List<Region>, tlbEntries: Int = 64) {
    val pageTable = PageTable()
    val tlb = Tlb(tlbEntries)

    var tlbHits = 0L; private set
    /** Every access the TLB could not answer, page faults and segfaults included. */
    var tlbMisses = 0L; private set
    var pageFaults = 0L; private set
    var segfaults = 0L; private set
    /** Memory reads the hardware spent walking the page table: one per level on every TLB miss. */
    var walkReads = 0L; private set

    private var nextFreeFrame = 0L

    /**
     * Translate [va]: try the TLB, then walk the page table, then fault. On a fault inside a [Region]
     * the kernel takes a free frame, maps it, and the access succeeds. Outside every region it is a segfault.
     */
    fun access(va: Long): Outcome {
        TODO("TLB hit, else walk (4 reads): a mapped page is a TLB miss, an address in a region is a page fault (map a new frame), anything else is a segfault")
    }
}
