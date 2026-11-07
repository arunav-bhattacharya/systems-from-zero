package sfz.internals.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import org.junit.jupiter.api.io.TempDir
import java.nio.file.Path

class BufferPoolTest {
    /** fetch then unpin: one quick "use" of a page, as a query touching it would. */
    private fun BufferPool.touch(vararg pageIds: Int) {
        for (id in pageIds) {
            fetch(id)
            unpin(id, dirty = false)
        }
    }

    @Test
    fun `a miss reads the page from disk, a hit does no disk I-O`() {
        val disk = InMemoryDisk(pages = 10)
        val pool = BufferPool(disk, capacity = 4)
        val f = pool.fetch(7)
        assertThat(f.pageId).isEqualTo(7)
        assertThat(f.data.getInt(0)).`as`("the frame holds page 7's bytes").isEqualTo(7)
        assertThat(disk.readsOf(7)).isEqualTo(1)
        pool.unpin(7, dirty = false)
        repeat(5) { pool.touch(7) }
        assertThat(disk.totalReads).`as`("disk reads after five more fetches of page 7").isEqualTo(1)
        assertThat(disk.totalWrites).isZero()
    }

    @Test
    fun `free frames are used before anything is evicted`() {
        val disk = InMemoryDisk(pages = 10)
        val pool = BufferPool(disk, capacity = 4)
        pool.touch(1, 2, 3, 4)
        assertThat(pool.cachedPages()).containsExactlyInAnyOrder(1, 2, 3, 4)
        assertThat(disk.totalReads).isEqualTo(4)
    }

    @Test
    fun `fetch pins the page, and two fetches need two unpins before it can be evicted`() {
        val disk = InMemoryDisk(pages = 10)
        val pool = BufferPool(disk, capacity = 1)
        pool.fetch(1)
        pool.fetch(1)
        pool.unpin(1, dirty = false)
        assertThrows<NoFreeFrameException> { pool.fetch(2) }
        pool.unpin(1, dirty = false)
        assertThat(pool.fetch(2).pageId).isEqualTo(2)
        assertThat(pool.cachedPages()).containsExactly(2)
    }

    @Test
    fun `with every frame pinned, fetch and newPage throw NoFreeFrameException and change nothing`() {
        val disk = InMemoryDisk(pages = 10)
        val pool = BufferPool(disk, capacity = 3)
        pool.fetch(1); pool.fetch(2); pool.fetch(3)
        assertThrows<NoFreeFrameException> { pool.fetch(4) }
        assertThrows<NoFreeFrameException> { pool.newPage() }
        assertThat(pool.cachedPages()).containsExactlyInAnyOrder(1, 2, 3)
        assertThat(disk.readsOf(4)).isZero()
        assertThat(disk.pageCount).`as`("newPage must not allocate a page it cannot hold").isEqualTo(10)
    }

    @Test
    fun `unpinning a page that is not pinned is a bug in the caller`() {
        val pool = BufferPool(InMemoryDisk(pages = 10), capacity = 2)
        pool.fetch(1)
        pool.unpin(1, dirty = false)
        assertThrows<IllegalStateException> { pool.unpin(1, dirty = false) }
        assertThrows<IllegalStateException> { pool.unpin(9, dirty = false) }
    }

    @Test
    fun `a dirty victim is written back exactly once, a clean victim never`() {
        val disk = InMemoryDisk(pages = 10)
        val pool = BufferPool(disk, capacity = 2)
        pool.fetch(1).data.putInt(100, 4242)                  // change page 1 in memory
        pool.unpin(1, dirty = true)
        pool.touch(2)
        pool.touch(3)                                         // evicts page 1
        pool.touch(4)                                         // evicts page 2
        assertThat(pool.cachedPages()).containsExactlyInAnyOrder(3, 4)
        assertThat(disk.writesOf(1)).`as`("writes of dirty page 1").isEqualTo(1)
        assertThat(disk.writesOf(2)).`as`("writes of clean page 2").isZero()
        assertThat(disk.bytesOf(1).getInt(100)).`as`("page 1 on disk").isEqualTo(4242)
        assertThat(pool.fetch(1).data.getInt(100)).`as`("page 1 read back").isEqualTo(4242)
    }

    @Test
    fun `a clean unpin does not undo an earlier dirty unpin`() {
        val disk = InMemoryDisk(pages = 10)
        val pool = BufferPool(disk, capacity = 1)
        pool.fetch(1).data.putInt(8, 77)
        pool.unpin(1, dirty = true)
        pool.fetch(1)
        pool.unpin(1, dirty = false)
        pool.touch(2)                                         // evicts page 1
        assertThat(disk.writesOf(1)).isEqualTo(1)
        assertThat(disk.bytesOf(1).getInt(8)).isEqualTo(77)
    }

    @Test
    fun `the usage count starts at 1, rises by one per fetch and stops at 5`() {
        val pool = BufferPool(InMemoryDisk(pages = 10), capacity = 2)
        val f = pool.fetch(3)
        pool.unpin(3, dirty = false)
        assertThat(f.usageCount).isEqualTo(1)
        pool.touch(3)
        assertThat(f.usageCount).isEqualTo(2)
        repeat(10) { pool.touch(3) }
        assertThat(f.usageCount).isEqualTo(BufferPool.MAX_USAGE)
    }

    @Test
    fun `CLOCK gives a recently used page a second chance - pattern 1,2,3,1,4 evicts page 2`() {
        val pool = BufferPool(InMemoryDisk(pages = 10), capacity = 3)
        pool.touch(1, 2, 3, 1)
        pool.touch(4)
        assertThat(pool.cachedPages()).`as`("after 1,2,3,1,4").containsExactlyInAnyOrder(1, 3, 4)
        // the hand stopped just past page 4's frame, so page 3 (usage now 0) is the next victim
        pool.touch(5)
        assertThat(pool.cachedPages()).`as`("after 5").containsExactlyInAnyOrder(1, 4, 5)
    }

    @Test
    fun `the hand skips pinned frames and leaves their usage count alone`() {
        val pool = BufferPool(InMemoryDisk(pages = 10), capacity = 3)
        val pinned = pool.fetch(1)                            // stays pinned for the whole test
        pool.touch(2, 3)
        pool.touch(4)
        assertThat(pool.cachedPages()).containsExactlyInAnyOrder(1, 3, 4)
        assertThat(pinned.usageCount).`as`("usage count of the pinned page").isEqualTo(1)
        pool.touch(5, 6, 7, 8)
        assertThat(pool.cachedPages()).`as`("a pinned page never leaves").contains(1)
    }

    @Test
    fun `newPage gives a zeroed, pinned, dirty page that reaches the disk on flush`() {
        val disk = InMemoryDisk(pages = 3)
        val pool = BufferPool(disk, capacity = 1)
        pool.touch(2)                                         // the only frame now holds page 2's bytes
        val f = pool.newPage()
        assertThat(f.pageId).isEqualTo(3)
        assertThat(f.pinCount).isEqualTo(1)
        assertThat(f.dirty).isTrue()
        assertThat(f.data.array().all { it == 0.toByte() }).`as`("the new page is all zeros").isTrue()
        f.data.putInt(0, 9001)
        pool.unpin(3, dirty = true)
        pool.flushAll()
        assertThat(disk.writesOf(3)).isEqualTo(1)
        assertThat(disk.bytesOf(3).getInt(0)).isEqualTo(9001)
    }

    @Test
    fun `flushAll writes each dirty page once, skips clean pages, and leaves them clean`() {
        val disk = InMemoryDisk(pages = 10)
        val pool = BufferPool(disk, capacity = 4)
        for (id in 1..4) {
            pool.fetch(id).data.putInt(4, id * 10)
            pool.unpin(id, dirty = id % 2 == 0)
        }
        pool.flushAll()
        assertThat(disk.writes).containsOnlyKeys(2, 4)
        assertThat(disk.totalWrites).isEqualTo(2)
        pool.flushAll()
        pool.touch(5, 6, 7, 8)                                 // evict all four
        assertThat(disk.totalWrites).`as`("no page is written twice").isEqualTo(2)
    }

    @Test
    fun `pages written through the pool are there after a restart`(@TempDir dir: Path) {
        val file = dir.resolve("heap.db")
        FileDiskManager(file).use { disk ->
            val pool = BufferPool(disk, capacity = 2)
            repeat(5) {
                val f = pool.newPage()
                f.data.putInt(0, 1000 + f.pageId)
                pool.unpin(f.pageId, dirty = true)
            }
            pool.flushAll()
            disk.sync()
        }
        FileDiskManager(file).use { disk ->
            assertThat(disk.pageCount).isEqualTo(5)
            val pool = BufferPool(disk, capacity = 2)
            for (id in 0 until 5) {
                assertThat(pool.fetch(id).data.getInt(0)).`as`("page $id").isEqualTo(1000 + id)
                pool.unpin(id, dirty = false)
            }
        }
    }
}
