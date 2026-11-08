package sfz.enc.l05

import io.temporal.activity.ActivityOptions
import io.temporal.activity.setRetryOptions
import io.temporal.failure.ActivityFailure
import io.temporal.workflow.Workflow
import java.time.Duration

/** Version 1 of the order workflow, as it ran in production before the fraud check: the tests start runs on it. */
class OrderWorkflowV1 : OrderWorkflow {
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
        val id = Workflow.getInfo().workflowId
        val chargeId = activities.charge("$id/charge", orderId, amountCents)
        val reservationId = try {
            activities.reserve("$id/reserve", orderId, sku)
        } catch (e: ActivityFailure) {
            activities.refund("$id/refund", chargeId)
            return "REFUNDED"
        }
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
