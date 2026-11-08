package sfz.enc.l05

import io.temporal.activity.ActivityOptions
import io.temporal.activity.setRetryOptions
import io.temporal.failure.ActivityFailure
import io.temporal.workflow.Workflow
import java.time.Duration

class OrderWorkflowImpl : OrderWorkflow {
    // a stub, not the activities themselves: each call becomes a ScheduleActivityTask command
    private val activities: OrderActivities = Workflow.newActivityStub(
        OrderActivities::class.java,
        ActivityOptions {
            setStartToCloseTimeout(Duration.ofSeconds(10))
            setRetryOptions {
                setInitialInterval(Duration.ofSeconds(1))
                setMaximumAttempts(5)
            }
        },
    )

    override fun process(orderId: String, amountCents: Long, sku: String): String {
        // 1. the change: runs started before it have no marker and replay as DEFAULT_VERSION (-1)
        val version = Workflow.getVersion(FRAUD_CHECK_CHANGE, Workflow.DEFAULT_VERSION, 1)
        if (version >= 1 && !activities.checkFraud(orderId, amountCents)) return "REJECTED"

        // 2. one key per step, built from the workflow id: the same on every retry and every replay
        val id = Workflow.getInfo().workflowId
        val chargeId = activities.charge("$id/charge", orderId, amountCents)

        // 3. a step that fails for good: undo what is done, newest first
        val reservationId = try {
            activities.reserve("$id/reserve", orderId, sku)
        } catch (e: ActivityFailure) {
            activities.refund("$id/refund", chargeId)
            return "REFUNDED"
        }

        // 4. a durable timer: a TimerStarted event in the history, not a sleeping thread
        Workflow.sleep(PICKUP_WAIT)

        try {
            activities.ship("$id/ship", orderId, reservationId)
        } catch (e: ActivityFailure) {
            activities.release("$id/release", reservationId)
            activities.refund("$id/refund", chargeId)
            return "CANCELLED"
        }
        return "SHIPPED"
    }
}
