package sfz.enc.l05

import io.temporal.activity.ActivityOptions
import io.temporal.activity.setRetryOptions
import io.temporal.workflow.Workflow
import java.time.Duration

/**
 * The order workflow. Version 1 is already running in production. It did, in this order:
 *
 *     charge(key, orderId, amountCents) -> reserve(key, orderId, sku) -> Workflow.sleep(PICKUP_WAIT) -> ship(key, ...)
 *
 * and returned "SHIPPED". Write [process] so that it does the same, plus three things:
 *
 * 1. Idempotency keys. Pass every activity a key built from the workflow id and the step name,
 *    `"${Workflow.getInfo().workflowId}/charge"` and so on. It is the same on every retry and every replay.
 *    Never `UUID.randomUUID()` in workflow code: replay would make a different one.
 * 2. Compensation (a saga). An activity that fails for good reaches the workflow as an
 *    `io.temporal.failure.ActivityFailure`. If `reserve` fails: refund the charge, return "REFUNDED".
 *    If `ship` fails: release the reservation, then refund, return "CANCELLED".
 * 3. A new first step, the fraud check, released under the change id [FRAUD_CHECK_CHANGE].
 *    Runs that started on version 1 are in flight right now, asleep in their 24-hour wait. When they
 *    wake up on this code, replay must see the same commands as before. So ask
 *    `Workflow.getVersion(FRAUD_CHECK_CHANGE, Workflow.DEFAULT_VERSION, 1)` first, and call
 *    `checkFraud` only when the answer is 1. If it returns false, return "REJECTED" before charging.
 *
 * Call the activities directly on [activities]. Don't pass method references such as
 * `activities::charge` to `Async` or `Saga` (the lesson explains what Kotlin 2.4 changed).
 */
class OrderWorkflowImpl : OrderWorkflow {
    // finished: a stub, not the activities themselves; each call becomes a ScheduleActivityTask command
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
        TODO("getVersion and the fraud check, then charge, reserve, wait, ship, with keys and compensations")
    }
}
