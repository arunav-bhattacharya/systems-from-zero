package sfz.enc.l05

import io.temporal.failure.ApplicationFailure
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

// Finished: the activities. Each one calls the outside world once and counts how often it ran.
// You don't change this file.

/**
 * Activity implementations backed by a [World].
 *
 * [crashAfter] lists steps (for example `"charge"`) whose FIRST execution does its side effect and then
 * fails before it can report success, the way a worker does when it is killed at exactly the wrong moment.
 * Temporal sees a failed attempt and runs the step again.
 */
class OrderActivitiesImpl(
    private val world: World,
    private val crashAfter: Set<String> = emptySet(),
) : OrderActivities {
    private val runs = ConcurrentHashMap<String, AtomicInteger>()

    /** How many times this worker started the activity [name] ("charge", "reserve", ...). */
    fun executions(name: String): Int = runs[name]?.get() ?: 0

    private fun <T> step(name: String, sideEffect: () -> T): T {
        val attempt = runs.computeIfAbsent(name) { AtomicInteger() }.incrementAndGet()
        val result = try {
            sideEffect()
        } catch (e: PermanentFailure) {
            // retrying cannot help: tell Temporal not to retry, and say why
            throw ApplicationFailure.newNonRetryableFailure(e.message, e.type)
        }
        if (name in crashAfter && attempt == 1) {
            throw IllegalStateException("worker died after $name took effect, before it reported back")
        }
        return result
    }

    override fun checkFraud(orderId: String, amountCents: Long): Boolean =
        step("checkFraud") { amountCents <= world.fraudLimitCents }

    override fun charge(idempotencyKey: String, orderId: String, amountCents: Long): String =
        step("charge") { world.bank.charge(idempotencyKey, orderId, amountCents) }

    override fun reserve(idempotencyKey: String, orderId: String, sku: String): String =
        step("reserve") { world.warehouse.reserve(idempotencyKey, orderId, sku) }

    override fun ship(idempotencyKey: String, orderId: String, reservationId: String): String =
        step("ship") { world.courier.ship(idempotencyKey, orderId) }

    override fun refund(idempotencyKey: String, chargeId: String) =
        step("refund") { world.bank.refund(idempotencyKey, chargeId) }

    override fun release(idempotencyKey: String, reservationId: String) =
        step("release") { world.warehouse.release(idempotencyKey, reservationId) }
}
