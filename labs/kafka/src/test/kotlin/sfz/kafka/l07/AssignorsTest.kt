package sfz.kafka.l07

import org.apache.kafka.common.TopicPartition
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** The two classic eager assignors, checked by hand-worked examples. No broker needed. */
class AssignorsTest {
    private fun tp(topic: String, vararg ps: Int) = ps.map { TopicPartition(topic, it) }

    @Test
    fun `range gives each member a contiguous block, and the first members the extra partitions`() {
        val result = Assignors.range(listOf("c3", "c1", "c2"), mapOf("payments" to 7))
        assertThat(result).isEqualTo(
            mapOf("c1" to tp("payments", 0, 1, 2), "c2" to tp("payments", 3, 4), "c3" to tp("payments", 5, 6)),
        )
    }

    @Test
    fun `range works topic by topic, so the same member gets the extra partition of every topic`() {
        val result = Assignors.range(listOf("c1", "c2"), mapOf("payments" to 3, "refunds" to 3))
        assertThat(result.getValue("c1")).isEqualTo(tp("payments", 0, 1) + tp("refunds", 0, 1)) // 4 partitions
        assertThat(result.getValue("c2")).isEqualTo(tp("payments", 2) + tp("refunds", 2))       // 2 partitions
    }

    @Test
    fun `round robin deals all partitions like cards, so two topics still split 3 and 3`() {
        val result = Assignors.roundRobin(listOf("c2", "c1"), mapOf("refunds" to 3, "payments" to 3))
        assertThat(result.getValue("c1")).isEqualTo(tp("payments", 0, 2) + tp("refunds", 1))
        assertThat(result.getValue("c2")).isEqualTo(tp("payments", 1) + tp("refunds", 0, 2))
    }

    @Test
    fun `a member beyond the partition count gets nothing, but still appears in the result`() {
        for (assignment in listOf(
            Assignors.range(listOf("c1", "c2", "c3"), mapOf("payments" to 2)),
            Assignors.roundRobin(listOf("c1", "c2", "c3"), mapOf("payments" to 2)),
        )) {
            assertThat(assignment.keys).containsExactlyInAnyOrder("c1", "c2", "c3")
            assertThat(assignment.getValue("c3")).isEmpty()
            assertThat(assignment.values.flatten()).containsExactlyInAnyOrderElementsOf(tp("payments", 0, 1))
        }
    }
}
