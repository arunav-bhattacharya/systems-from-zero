package sfz.msg.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** The compaction model. No broker needed. */
class CompactionTest {
    private val day = 86_400_000L
    private val now = 30 * day

    // the card-status topic from the lesson, as closed-segment records
    private val cardStatus = listOf(
        Rec(0, "card-1", "active", now - 3 * 3_600_000),
        Rec(1, "card-2", "active", now - 3 * 3_600_000),
        Rec(2, "card-1", "frozen", now - 2 * 3_600_000),
        Rec(3, "card-3", "active", now - 2 * 3_600_000),
        Rec(4, "card-1", "active", now - 3_600_000),
        Rec(5, "card-2", null, now - 3_600_000), // tombstone: card-2 is deleted
    )

    @Test
    fun `keeps only the last record of each key, with its original offset`() {
        val kept = Compaction.compact(cardStatus, now, day)
        assertThat(kept.map { it.offset }).containsExactly(3L, 4L, 5L)
        assertThat(kept.associate { it.key to it.value })
            .containsEntry("card-1", "active")
            .containsEntry("card-3", "active")
    }

    @Test
    fun `survivors stay in offset order and offsets are never rewritten`() {
        val kept = Compaction.compact(cardStatus, now, day)
        assertThat(kept).isEqualTo(listOf(cardStatus[3], cardStatus[4], cardStatus[5]))
    }

    @Test
    fun `a young tombstone stays so consumers can see the delete`() {
        val kept = Compaction.compact(cardStatus, now, day)
        assertThat(kept.filter { it.key == "card-2" }).containsExactly(cardStatus[5])
    }

    @Test
    fun `a tombstone older than delete retention goes away, and so does the key`() {
        val later = now + 2 * day
        val kept = Compaction.compact(cardStatus, later, day)
        assertThat(kept.map { it.key }).containsExactly("card-3", "card-1")
    }

    @Test
    fun `a key written once is untouched, and the input list is not changed`() {
        val input = listOf(Rec(10, "card-9", "active", now), Rec(11, "card-8", "active", now))
        val copy = input.toList()
        assertThat(Compaction.compact(input, now, day)).isEqualTo(input)
        assertThat(input).isEqualTo(copy)
    }

    @Test
    fun `a value written after a tombstone brings the key back`() {
        val input = cardStatus + Rec(6, "card-2", "active", now)
        val kept = Compaction.compact(input, now, day)
        assertThat(kept.map { it.offset }).containsExactly(3L, 4L, 6L)
    }
}
