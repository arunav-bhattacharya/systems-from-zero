package sfz.msg.l08

import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * The sticky assignor, step by step through a group that grows from one consumer to three and shrinks again.
 * The expected assignments are the ones a Kafka 4.4 broker's `uniform` assignor produced for the same group.
 */
class StickyAssignorTest {
    private val six = (0 until 6).map { TopicPartition("payments", it) }
    private fun p(vararg ps: Int) = ps.map { TopicPartition("payments", it) }

    @Test
    fun `the first member gets everything`() {
        assertThat(StickyAssignor.assign(listOf("c1"), six, emptyMap())).isEqualTo(mapOf("c1" to six))
    }

    @Test
    fun `a second member takes half, and the first keeps the other half without interruption`() {
        val before = mapOf("c1" to six)
        val after = StickyAssignor.assign(listOf("c1", "c2"), six, before)
        assertThat(after).isEqualTo(mapOf("c1" to p(0, 1, 2), "c2" to p(3, 4, 5)))
        assertThat(StickyAssignor.toRevoke(before, after)).isEqualTo(mapOf("c1" to p(3, 4, 5).toSet()))
    }

    @Test
    fun `a third member takes one partition from each of the others`() {
        val before = mapOf("c1" to p(0, 1, 2), "c2" to p(3, 4, 5))
        val after = StickyAssignor.assign(listOf("c1", "c2", "c3"), six, before)
        assertThat(after).isEqualTo(mapOf("c1" to p(0, 1), "c2" to p(3, 4), "c3" to p(2, 5)))
        assertThat(StickyAssignor.toRevoke(before, after)).isEqualTo(mapOf("c1" to p(2).toSet(), "c2" to p(5).toSet()))
    }

    @Test
    fun `when a member leaves, only its partitions move`() {
        val before = mapOf("c1" to p(0, 1), "c2" to p(3, 4), "c3" to p(2, 5))
        val after = StickyAssignor.assign(listOf("c1", "c3"), six, before)
        assertThat(after.getValue("c1")).hasSize(3).containsAll(p(0, 1))
        assertThat(after.getValue("c3")).hasSize(3).containsAll(p(2, 5))
        assertThat(after.values.flatten()).containsExactlyInAnyOrderElementsOf(six)
        val revoked = StickyAssignor.toRevoke(before, after)
        assertThat(revoked["c1"]).isEmpty()
        assertThat(revoked["c3"]).isEmpty()
    }

    @Test
    fun `the extra slot goes to the member that owned the most, so fewer partitions move`() {
        val seven = (0 until 7).map { TopicPartition("payments", it) }
        val before = mapOf("a" to p(0, 1, 2, 3, 4, 5), "b" to p(6))
        val after = StickyAssignor.assign(listOf("a", "b"), seven, before)
        assertThat(after).isEqualTo(mapOf("a" to p(0, 1, 2, 3), "b" to p(4, 5, 6)))
        assertThat(StickyAssignor.toRevoke(before, after).values.sumOf { it.size }).isEqualTo(2)
    }

    @Test
    fun `members and partitions that are gone are ignored, and the result is balanced`() {
        val ten = (0 until 10).map { TopicPartition("payments", it) }
        val before = mapOf(
            "c1" to (0 until 10).map { TopicPartition("payments", it) } + TopicPartition("payments", 11), // 11 is gone
            "c9" to p(7, 8),                                                                            // c9 left
        )
        val after = StickyAssignor.assign(listOf("c4", "c1", "c3", "c2"), ten, before)
        assertThat(after.keys).containsExactlyInAnyOrder("c1", "c2", "c3", "c4")
        assertThat(after.values.map { it.size }.sorted()).isEqualTo(listOf(2, 2, 3, 3))
        assertThat(after.values.flatten()).containsExactlyInAnyOrderElementsOf(ten)
        assertThat(after.getValue("c1")).isEqualTo(p(0, 1, 2)) // c1 keeps as much as its quota allows
        assertThat(StickyAssignor.assign(listOf("c4", "c1", "c3", "c2"), ten, before)).isEqualTo(after)
    }
}
