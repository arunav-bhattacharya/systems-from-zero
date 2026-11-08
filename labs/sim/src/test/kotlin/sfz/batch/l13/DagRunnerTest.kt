package sfz.batch.l13

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import java.time.LocalDate

class DagRunnerTest {
    private val day = LocalDate.of(2026, 11, 6)
    private fun noop(id: String, vararg deps: String) = Task(id, deps.toList(), minutes = 1) {}

    @Test
    fun `tasks come after their dependencies, and ready tasks go in id order`() {
        val dag = Dag(listOf(noop("report", "load", "fraud"), noop("load", "extract"), noop("fraud", "extract"), noop("extract"), noop("audit")))
        assertThat(dag.topologicalOrder().map { it.id }).containsExactly("audit", "extract", "fraud", "load", "report")
        assertThat(PaymentTasks.dag(PaymentTasks::appendDailyTotal).topologicalOrder().map { it.id }).containsExactly("extract", "load", "report")
    }

    @Test
    fun `a graph with a cycle is refused`() {
        val dag = Dag(listOf(noop("a", "c"), noop("b", "a"), noop("c", "b"), noop("d")))
        assertThatThrownBy { dag.topologicalOrder() }.isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `a clean run takes the sum of its task times`() {
        val w = Warehouse()
        val r = DagRunner().run(PaymentTasks.dag(PaymentTasks::appendDailyTotal), day, w, startMinute = 100)
        assertThat(r.states.values).containsOnly(TaskState.SUCCESS)
        assertThat(r.attempts).isEqualTo(mapOf("extract" to 1, "load" to 1, "report" to 1))
        assertThat(r.startMinute to r.endMinute).isEqualTo(100L to 120L)
        assertThat(w.read("daily_totals", day)).containsExactly(Source.total(day))
    }

    @Test
    fun `a task that crashes twice succeeds on its third attempt, after two retry delays`() {
        val faults = Faults(mapOf(("load" to day) to 2))
        val r = DagRunner(maxRetries = 2, retryDelayMinutes = 5).run(PaymentTasks.dag(PaymentTasks::appendDailyTotal, faults), day, Warehouse())
        assertThat(r.states["load"]).isEqualTo(TaskState.SUCCESS)
        assertThat(r.attempts["load"]).isEqualTo(3)
        // extract 5, load 3 x 10 with 2 x 5 of waiting, report 5
        assertThat(r.endMinute).isEqualTo(50)
    }

    @Test
    fun `a task that keeps failing is FAILED, and what depends on it never runs`() {
        val faults = Faults(mapOf(("load" to day) to 3))
        val w = Warehouse()
        val r = DagRunner(maxRetries = 2, retryDelayMinutes = 5).run(PaymentTasks.dag(PaymentTasks::appendDailyTotal, faults), day, w)
        assertThat(r.states).isEqualTo(mapOf("extract" to TaskState.SUCCESS, "load" to TaskState.FAILED, "report" to TaskState.UPSTREAM_FAILED))
        assertThat(r.attempts).isEqualTo(mapOf("extract" to 1, "load" to 3, "report" to 0))
        assertThat(r.endMinute).isEqualTo(5L + 3 * 10 + 2 * 5)
        assertThat(w.partitions("reports")).describedAs("report never ran").isEmpty()
    }

    @Test
    fun `with no retries the first crash fails the task`() {
        val faults = Faults(mapOf(("extract" to day) to 1))
        val r = DagRunner(maxRetries = 0).run(PaymentTasks.dag(PaymentTasks::appendDailyTotal, faults), day, Warehouse())
        assertThat(r.states["extract"]).isEqualTo(TaskState.FAILED)
        assertThat(r.attempts["extract"]).isEqualTo(1)
        assertThat(r.endMinute).isEqualTo(5)
    }
}
