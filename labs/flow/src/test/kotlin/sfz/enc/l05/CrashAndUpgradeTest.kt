package sfz.enc.l05

import io.temporal.api.enums.v1.EventType
import io.temporal.testing.WorkflowReplayer
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.util.concurrent.TimeUnit

/** Workers that stop in the middle of an order, and code that changes under orders still in flight. */
@Timeout(30, unit = TimeUnit.SECONDS)
class CrashAndUpgradeTest {

    @Test
    fun `a worker stopped mid-order is replaced, and the new one finishes without redoing finished steps`() {
        OrderHarness().use { h ->
            val first = h.startWorker()
            val order = h.start("order-7")
            h.awaitEvent("order-7", EventType.EVENT_TYPE_TIMER_STARTED) // charged, reserved, now asleep
            first.stop()

            val second = h.startWorker() // a new process: no memory of the order, only the history
            assertThat(order.getResult(String::class.java)).isEqualTo("SHIPPED")

            assertThat(first.activities.executions("charge")).isEqualTo(1)
            assertThat(first.activities.executions("reserve")).isEqualTo(1)
            assertThat(second.activities.executions("charge")).isEqualTo(0) // replayed from the history
            assertThat(second.activities.executions("reserve")).isEqualTo(0)
            assertThat(second.activities.executions("ship")).isEqualTo(1)
            assertThat(h.world.bank.chargesFor("order-7")).isEqualTo(1)
            assertThat(h.events("order-7").count { it == EventType.EVENT_TYPE_ACTIVITY_TASK_COMPLETED }).isEqualTo(4)
        }
    }

    @Test
    fun `a run started on version 1 wakes up on the new code and finishes without the fraud check`() {
        OrderHarness().use { h ->
            val old = h.startWorker(OrderWorkflowV1::class.java)
            val inFlight = h.start("order-8")
            h.awaitEvent("order-8", EventType.EVENT_TYPE_TIMER_STARTED)
            old.stop() // the deploy: version 1 goes away while order-8 sleeps

            val new = h.startWorker(OrderWorkflowImpl::class.java)
            assertThat(inFlight.getResult(String::class.java)).isEqualTo("SHIPPED")
            assertThat(new.activities.executions("ship")).isEqualTo(1) // the new code finished it
            assertThat(new.activities.executions("checkFraud")).isEqualTo(0) // and kept the old path
            assertThat(h.world.bank.chargesFor("order-8")).isEqualTo(1)

            assertThat(h.run("order-9")).isEqualTo("SHIPPED") // a new run takes the new path
            assertThat(new.activities.executions("checkFraud")).isEqualTo(1)
        }
    }

    @Test
    fun `the history of a version-1 run replays against the new code without a non-determinism error`() {
        val v1History = OrderHarness().use { h ->
            h.startWorker(OrderWorkflowV1::class.java)
            assertThat(h.run("order-10")).isEqualTo("SHIPPED")
            h.client.fetchHistory("order-10")
        }
        // what a CI test does with histories saved from production: throws if the new code would break them
        WorkflowReplayer.replayWorkflowExecution(v1History, OrderWorkflowImpl::class.java)
    }

    @Test
    fun `the new code replays its own history, so it has no hidden randomness or clock reads`() {
        val history = OrderHarness().use { h ->
            h.startWorker()
            assertThat(h.run("order-11")).isEqualTo("SHIPPED")
            h.client.fetchHistory("order-11")
        }
        assertThat(history.events.map { it.eventType }).contains(EventType.EVENT_TYPE_MARKER_RECORDED) // getVersion's marker
        WorkflowReplayer.replayWorkflowExecution(history, OrderWorkflowImpl::class.java)
    }
}
