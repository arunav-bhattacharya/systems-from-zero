package sfz.internals.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import sfz.internals.l02.SlottedPage.Companion.HEADER_SIZE
import sfz.internals.l02.SlottedPage.Companion.PAGE_SIZE
import sfz.internals.l02.SlottedPage.Companion.SLOT_SIZE
import java.nio.ByteBuffer

class SlottedPageTest {
    /** A recognisable record: "auth-<n>:" padded with the letter for n, to exactly [size] bytes. */
    private fun rec(n: Int, size: Int): ByteArray {
        val tag = "auth-$n:".encodeToByteArray()
        return ByteArray(size) { i -> if (i < tag.size) tag[i] else ('a' + n % 26).code.toByte() }
    }

    private fun full(size: Int): Pair<SlottedPage, List<Int>> {
        val page = SlottedPage.empty()
        val slots = generateSequence(0) { it + 1 }.map { page.insert(rec(it, size)) }.takeWhile { it != null }.map { it!! }.toList()
        return page to slots
    }

    @Test
    fun `an empty page has no slots and all its space free`() {
        val page = SlottedPage.empty()
        assertThat(page.slotCount()).isZero()
        assertThat(page.freeSpace()).isEqualTo(PAGE_SIZE - HEADER_SIZE)
    }

    @Test
    fun `insert hands out slot ids 0, 1, 2 and get returns the same bytes`() {
        val page = SlottedPage.empty()
        assertThat(page.insert(rec(0, 40))).isEqualTo(0)
        assertThat(page.insert(rec(1, 75))).isEqualTo(1)
        assertThat(page.insert(rec(2, 9))).isEqualTo(2)
        assertThat(page.get(0)).isEqualTo(rec(0, 40))
        assertThat(page.get(1)).isEqualTo(rec(1, 75))
        assertThat(page.get(2)).isEqualTo(rec(2, 9))
        assertThat(page.freeSpace()).isEqualTo(PAGE_SIZE - HEADER_SIZE - 3 * SLOT_SIZE - (40 + 75 + 9))
    }

    @Test
    fun `the bytes follow the layout - slots grow from the front, records from the back`() {
        val page = SlottedPage.empty()
        page.insert(rec(0, 10)); page.insert(rec(1, 20)); page.insert(rec(2, 30))
        val b = ByteBuffer.wrap(page.toBytes())
        fun u16(at: Int) = b.getShort(at).toInt() and 0xFFFF
        assertThat(u16(0)).`as`("lower: end of the slot array").isEqualTo(HEADER_SIZE + 3 * SLOT_SIZE)
        assertThat(u16(2)).`as`("upper: start of the records").isEqualTo(PAGE_SIZE - 60)
        assertThat(u16(4)).`as`("slot 0 offset").isEqualTo(PAGE_SIZE - 10)
        assertThat(u16(6)).`as`("slot 0 length").isEqualTo(10)
        assertThat(u16(8)).`as`("slot 1 offset").isEqualTo(PAGE_SIZE - 30)
        assertThat(u16(12)).`as`("slot 2 offset").isEqualTo(PAGE_SIZE - 60)
    }

    @Test
    fun `insert returns null exactly when the record and its slot no longer fit`() {
        val (page, slots) = full(100)
        // each record costs 100 bytes plus a 4-byte slot: 39 fit in 4,092 bytes, leaving 36
        assertThat(slots).hasSize(39)
        assertThat(page.freeSpace()).isEqualTo(36)
        assertThat(page.insert(rec(99, 33))).`as`("33 + 4 > 36").isNull()
        assertThat(page.insert(rec(99, 32))).`as`("32 + 4 = 36 fits exactly").isEqualTo(39)
        assertThat(page.freeSpace()).isZero()
        assertThat(page.insert(rec(100, 1))).isNull()
        for (s in slots) assertThat(page.get(s)).isEqualTo(rec(s, 100))
    }

    @Test
    fun `a deleted slot reads as null and its id is never handed out again`() {
        val page = SlottedPage.empty()
        page.insert(rec(0, 50)); page.insert(rec(1, 50)); page.insert(rec(2, 50))
        page.delete(1)
        assertThat(page.get(1)).isNull()
        assertThat(page.get(0)).isEqualTo(rec(0, 50))
        assertThat(page.get(2)).isEqualTo(rec(2, 50))
        assertThat(page.insert(rec(3, 50))).`as`("the new record's slot id").isEqualTo(3)
        assertThat(page.slotCount()).isEqualTo(4)
    }

    @Test
    fun `delete alone does not free contiguous space`() {
        val page = SlottedPage.empty()
        page.insert(rec(0, 200)); page.insert(rec(1, 200))
        val before = page.freeSpace()
        page.delete(0)
        assertThat(page.freeSpace()).isEqualTo(before)
    }

    @Test
    fun `compact keeps every live record under its slot id and frees the deleted bytes`() {
        val (page, slots) = full(100)
        val before = page.freeSpace()
        val gone = listOf(0, 7, 8, 21, 38)
        gone.forEach(page::delete)
        page.compact()
        assertThat(page.freeSpace()).isEqualTo(before + gone.size * 100)
        for (s in slots) {
            if (s in gone) assertThat(page.get(s)).`as`("deleted slot $s").isNull()
            else assertThat(page.get(s)).`as`("slot $s after compaction").isEqualTo(rec(s, 100))
        }
        assertThat(page.slotCount()).`as`("compaction never removes slots").isEqualTo(slots.size)
    }

    @Test
    fun `insert compacts by itself when the holes make room`() {
        val (page, slots) = full(100)
        listOf(3, 10, 20).forEach(page::delete)                     // 300 bytes of holes, 36 contiguous
        assertThat(page.insert(rec(500, 250))).`as`("250 + 4 fits in 36 + 300 after compaction").isEqualTo(39)
        assertThat(page.get(39)).isEqualTo(rec(500, 250))
        for (s in slots) if (s !in listOf(3, 10, 20)) assertThat(page.get(s)).`as`("slot $s").isEqualTo(rec(s, 100))
        assertThat(page.insert(rec(501, 79))).`as`("only 82 bytes are left anywhere on the page").isNull()
        assertThat(page.insert(rec(502, 78))).isEqualTo(40)
    }

    @Test
    fun `a record bigger than a quarter of the page is refused`() {
        val page = SlottedPage.empty()
        assertThat(page.insert(rec(1, SlottedPage.MAX_RECORD))).isEqualTo(0)
        val e = assertThrows<RecordTooLargeException> { page.insert(rec(2, SlottedPage.MAX_RECORD + 1)) }
        assertThat(e.size).isEqualTo(SlottedPage.MAX_RECORD + 1)
        assertThat(page.slotCount()).isEqualTo(1)
    }

    @Test
    fun `a page survives a round trip through its bytes`() {
        val page = SlottedPage.empty()
        for (i in 0 until 20) page.insert(rec(i, 30 + i * 7))
        page.delete(4); page.delete(11)
        val copy = SlottedPage.fromBytes(page.toBytes())
        assertThat(copy.toBytes()).isEqualTo(page.toBytes())
        assertThat(copy.freeSpace()).isEqualTo(page.freeSpace())
        assertThat(copy.slotCount()).isEqualTo(20)
        for (i in 0 until 20) {
            if (i == 4 || i == 11) assertThat(copy.get(i)).isNull() else assertThat(copy.get(i)).isEqualTo(rec(i, 30 + i * 7))
        }
        assertThat(copy.insert(rec(20, 30))).`as`("inserting into the reloaded page").isEqualTo(20)
    }
}
