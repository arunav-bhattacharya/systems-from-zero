package sfz.store.l03

import java.nio.ByteBuffer

/**
 * A fake disk for the buffer pool tests. It keeps pages in memory and counts every read and write per page.
 * Each of the first [pages] pages starts with its own page id as an int in bytes 0..3, so a test can tell pages apart.
 */
class InMemoryDisk(pages: Int = 0) : DiskManager {
    private val store = ArrayList<ByteArray>()
    val reads = HashMap<Int, Int>()
    val writes = HashMap<Int, Int>()

    init {
        repeat(pages) { id ->
            store += ByteBuffer.allocate(PAGE_SIZE).putInt(0, id).array()
        }
    }

    val pageCount: Int get() = store.size
    val totalReads: Int get() = reads.values.sum()
    val totalWrites: Int get() = writes.values.sum()
    fun readsOf(pageId: Int) = reads[pageId] ?: 0
    fun writesOf(pageId: Int) = writes[pageId] ?: 0

    /** A copy of what is on "disk" for [pageId]. */
    fun bytesOf(pageId: Int): ByteBuffer = ByteBuffer.wrap(store[pageId].copyOf())

    override fun readPage(pageId: Int, dst: ByteBuffer) {
        require(pageId in store.indices) { "page $pageId does not exist" }
        reads.merge(pageId, 1, Int::plus)
        dst.duplicate().clear().put(store[pageId])
    }

    override fun writePage(pageId: Int, src: ByteBuffer) {
        require(pageId in store.indices) { "page $pageId was never allocated" }
        writes.merge(pageId, 1, Int::plus)
        val copy = ByteArray(PAGE_SIZE)
        src.duplicate().clear().get(copy)
        store[pageId] = copy
    }

    override fun allocatePage(): Int {
        store += ByteArray(PAGE_SIZE)
        return store.size - 1
    }
}
