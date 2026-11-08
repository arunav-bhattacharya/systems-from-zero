package sfz.enc.l05

import io.temporal.activity.ActivityInterface
import io.temporal.workflow.WorkflowInterface
import io.temporal.workflow.WorkflowMethod
import java.time.Duration

// Finished: the contract between the workflow and its activities. You don't change this file.

/** The task queue the workers poll. A workflow and its activities can use different queues; here they share one. */
const val TASK_QUEUE = "orders"

/** The change id the fraud check is released under (see OrderWorkflowImpl). */
const val FRAUD_CHECK_CHANGE = "fraud-check"

/** The courier collects parcels once a day, so the workflow waits this long between reserving and shipping. */
val PICKUP_WAIT: Duration = Duration.ofHours(24)

/**
 * One order: take the money, hold the item, ship it. Temporal names the workflow type after the
 * interface, `OrderWorkflow`, so every implementation of it is the same workflow to the server.
 */
@WorkflowInterface
interface OrderWorkflow {
    /** Returns how the order ended: SHIPPED, REJECTED, REFUNDED or CANCELLED. */
    @WorkflowMethod
    fun process(orderId: String, amountCents: Long, sku: String): String
}

/**
 * The steps that touch the outside world. Each one runs in an activity worker, may be retried,
 * and takes an idempotency key so that a retried step can be recognized by the system it calls.
 */
@ActivityInterface
interface OrderActivities {
    /** True when the order may go ahead. */
    fun checkFraud(orderId: String, amountCents: Long): Boolean

    /** Charges the card and returns the charge id. */
    fun charge(idempotencyKey: String, orderId: String, amountCents: Long): String

    /** Holds one unit of [sku] and returns the reservation id. Fails for good (non-retryable) when out of stock. */
    fun reserve(idempotencyKey: String, orderId: String, sku: String): String

    /** Hands the parcel to the courier and returns the tracking id. Fails for good when the courier refuses it. */
    fun ship(idempotencyKey: String, orderId: String, reservationId: String): String

    /** Gives the money back: the compensation for [charge]. */
    fun refund(idempotencyKey: String, chargeId: String)

    /** Puts the unit back on the shelf: the compensation for [reserve]. */
    fun release(idempotencyKey: String, reservationId: String)
}
