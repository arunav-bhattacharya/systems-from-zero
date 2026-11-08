package sfz.batch.l06

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test

class StageModelTest {

    @Test
    fun `narrow steps stay in one stage with one task per input partition`() {
        val stages = StageModel.stages(listOf(Read("read payments", 8), Narrow("captured only"), Narrow("amount in euros")))
        assertThat(stages).containsExactly(Stage(listOf("read payments", "captured only", "amount in euros"), 8))
    }

    @Test
    fun `every wide step starts a new stage with its own number of tasks`() {
        val stages = StageModel.stages(
            listOf(
                Read("read payments", 4),
                Narrow("captured only"),
                Wide("total per merchant", 200),
                Narrow("big merchants only"),
                Wide("sort by total", 10),
            ),
        )
        assertThat(stages).containsExactly(
            Stage(listOf("read payments", "captured only"), 4),
            Stage(listOf("total per merchant", "big merchants only"), 200),
            Stage(listOf("sort by total"), 10),
        )
        assertThat(stages.sumOf { it.tasks }).isEqualTo(214)
    }

    @Test
    fun `a pipeline must start by reading exactly one input`() {
        assertThatThrownBy { StageModel.stages(emptyList()) }.isInstanceOf(IllegalArgumentException::class.java)
        assertThatThrownBy { StageModel.stages(listOf(Narrow("filter"), Read("payments", 2))) }
            .isInstanceOf(IllegalArgumentException::class.java)
        assertThatThrownBy { StageModel.stages(listOf(Read("payments", 2), Read("refunds", 2))) }
            .isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `tasks run in waves of one task per slot`() {
        assertThat(StageModel.waves(tasks = 8, slots = 2)).isEqualTo(4)
        assertThat(StageModel.waves(tasks = 9, slots = 4)).isEqualTo(3)
        assertThat(StageModel.waves(tasks = 3, slots = 16)).isEqualTo(1)
        assertThat(StageModel.waves(tasks = 0, slots = 4)).isEqualTo(0)
        // 200 shuffle partitions on a 12-core laptop: 17 waves, the last one only 8 tasks wide
        assertThat(StageModel.waves(tasks = 200, slots = 12)).isEqualTo(17)
    }
}
