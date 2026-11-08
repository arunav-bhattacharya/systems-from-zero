package sfz.store.l02

import java.nio.ByteBuffer

/**
 * A 4 KB slotted page, the layout PostgreSQL and SQLite use to keep variable-length records in fixed-size pages.
 *
 * ```
 * 0      2      4                lower                  upper                 4096
 * | lower| upper| slot 0| slot 1|...  free space  ...| record 1 | record 0 |
 *  header        slot array grows ->           <- records grow from the end
 * ```
 *
 * - The header holds two unsigned 16-bit offsets: `lower` (end of the slot array) and `upper` (start of the records).
 * - Slot `i` sits at `HEADER_SIZE + i * SLOT_SIZE` and holds the record's offset and length (16 bits each).
 *   A slot with length 0 is dead: its record was deleted.
 * - A slot id never changes and is never reused, so (page, slot) can identify a record for its whole life.
 *   [compact] moves records, never slots.
 *
 * Your job: write [insert], [get], [delete], [compact] and [freeSpace]. The header and slot helpers at the
 * bottom are done; use them instead of touching [buf] offsets by hand.
 */
class SlottedPage private constructor(private val buf: ByteBuffer) {

    /**
     * Stores [record] and returns its new slot id, or null if it does not fit even after compaction.
     *
     * - Throw [RecordTooLargeException] if `record.size > MAX_RECORD`, and [IllegalArgumentException] if it is empty.
     * - A record needs `record.size + SLOT_SIZE` bytes of contiguous free space. If [freeSpace] is too small but the
     *   holes left by deleted records would make enough room, [compact] first.
     * - New slots always go at the end of the slot array: slot id = [slotCount] before the insert.
     */
    fun insert(record: ByteArray): Int? {
        TODO("check the size, compact if the holes help, copy the record below `upper`, add a slot")
    }

    /** The bytes of the record in [slot], or null if it was deleted. Throws [IllegalArgumentException] for a slot that never existed. */
    fun get(slot: Int): ByteArray? {
        TODO("read the slot; length 0 means deleted; otherwise copy length bytes from offset")
    }

    /** Deletes the record in [slot]: mark the slot dead. Its bytes stay where they are until [compact]. */
    fun delete(slot: Int) {
        TODO("mark the slot dead")
    }

    /**
     * Slides every live record up against the end of the page so all free space is one contiguous gap.
     * Every live record keeps its slot id and its bytes; only the offsets in the slots change.
     */
    fun compact() {
        TODO("move live records to the end of the page, update their slot offsets and `upper`")
    }

    /** Contiguous free bytes between the slot array and the records: `upper - lower`. */
    fun freeSpace(): Int {
        TODO("upper - lower")
    }

    /** How many slots exist, live or dead. */
    fun slotCount(): Int = (lower - HEADER_SIZE) / SLOT_SIZE

    /** A copy of the page's 4096 bytes, exactly as they would be written to disk. */
    fun toBytes(): ByteArray = buf.array().copyOf()

    // ---- header and slot helpers (done) ----

    private var lower: Int
        get() = u16(0)
        set(v) = putU16(0, v)

    private var upper: Int
        get() = u16(2)
        set(v) = putU16(2, v)

    private fun slotAt(slot: Int) = HEADER_SIZE + slot * SLOT_SIZE
    private fun slotOffset(slot: Int): Int = u16(slotAt(slot))
    private fun slotLength(slot: Int): Int = u16(slotAt(slot) + 2)
    private fun setSlot(slot: Int, offset: Int, length: Int) {
        putU16(slotAt(slot), offset)
        putU16(slotAt(slot) + 2, length)
    }

    private fun u16(at: Int): Int = buf.getShort(at).toInt() and 0xFFFF
    private fun putU16(at: Int, v: Int) { buf.putShort(at, v.toShort()) }

    companion object {
        const val PAGE_SIZE = 4096
        const val HEADER_SIZE = 4
        const val SLOT_SIZE = 4
        /** Bigger records belong somewhere else (PostgreSQL moves them to a TOAST table). */
        const val MAX_RECORD = PAGE_SIZE / 4

        /** A fresh page: no slots, all free space. */
        fun empty(): SlottedPage {
            val p = SlottedPage(ByteBuffer.allocate(PAGE_SIZE))
            p.lower = HEADER_SIZE
            p.upper = PAGE_SIZE
            return p
        }

        /** A page read back from disk. */
        fun fromBytes(bytes: ByteArray): SlottedPage {
            require(bytes.size == PAGE_SIZE) { "a page is $PAGE_SIZE bytes, got ${bytes.size}" }
            return SlottedPage(ByteBuffer.wrap(bytes.copyOf()))
        }
    }
}

/** A record too big for one page. */
class RecordTooLargeException(val size: Int) :
    IllegalArgumentException("record of $size bytes is larger than ${SlottedPage.MAX_RECORD}; store it out of line")
