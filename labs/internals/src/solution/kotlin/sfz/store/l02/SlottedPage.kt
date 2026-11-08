package sfz.store.l02

import java.nio.ByteBuffer

class SlottedPage private constructor(private val buf: ByteBuffer) {

    fun insert(record: ByteArray): Int? {
        require(record.isNotEmpty()) { "empty records are not allowed: length 0 marks a dead slot" }
        if (record.size > MAX_RECORD) throw RecordTooLargeException(record.size)
        val need = record.size + SLOT_SIZE                    // the record plus its new slot
        if (freeSpace() < need) {
            // after compaction, free space = everything that is not header, slots or live records
            if (PAGE_SIZE - lower - liveBytes() < need) return null
            compact()
        }
        upper -= record.size                                  // records grow down from the end
        buf.put(upper, record)
        val slot = slotCount()
        setSlot(slot, upper, record.size)
        lower += SLOT_SIZE                                    // the slot array grows up from the header
        return slot
    }

    fun get(slot: Int): ByteArray? {
        require(slot in 0 until slotCount()) { "no slot $slot on this page" }
        val len = slotLength(slot)
        if (len == 0) return null                             // dead slot
        val out = ByteArray(len)
        buf.get(slotOffset(slot), out)
        return out
    }

    fun delete(slot: Int) {
        require(slot in 0 until slotCount()) { "no slot $slot on this page" }
        setSlot(slot, 0, 0)                                   // the bytes stay until compact(); the slot id is never reused
    }

    fun compact() {
        // live records, nearest the end of the page first, so each move only goes up into space already vacated
        val live = (0 until slotCount()).filter { slotLength(it) > 0 }.sortedByDescending { slotOffset(it) }
        var top = PAGE_SIZE
        val bytes = buf.array()
        for (slot in live) {
            val len = slotLength(slot)
            top -= len
            System.arraycopy(bytes, slotOffset(slot), bytes, top, len)   // safe for overlapping ranges
            setSlot(slot, top, len)                                      // same slot id, new offset
        }
        upper = top
    }

    fun freeSpace(): Int = upper - lower

    fun slotCount(): Int = (lower - HEADER_SIZE) / SLOT_SIZE

    fun toBytes(): ByteArray = buf.array().copyOf()

    private fun liveBytes(): Int = (0 until slotCount()).sumOf { slotLength(it) }

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
        const val MAX_RECORD = PAGE_SIZE / 4

        fun empty(): SlottedPage {
            val p = SlottedPage(ByteBuffer.allocate(PAGE_SIZE))
            p.lower = HEADER_SIZE
            p.upper = PAGE_SIZE
            return p
        }

        fun fromBytes(bytes: ByteArray): SlottedPage {
            require(bytes.size == PAGE_SIZE) { "a page is $PAGE_SIZE bytes, got ${bytes.size}" }
            return SlottedPage(ByteBuffer.wrap(bytes.copyOf()))
        }
    }
}

class RecordTooLargeException(val size: Int) :
    IllegalArgumentException("record of $size bytes is larger than ${SlottedPage.MAX_RECORD}; store it out of line")
