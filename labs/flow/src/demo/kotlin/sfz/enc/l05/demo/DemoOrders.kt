package sfz.enc.l05.demo

import io.temporal.activity.Activity
import io.temporal.activity.ActivityInterface
import io.temporal.activity.ActivityOptions
import io.temporal.activity.setRetryOptions
import io.temporal.api.history.v1.HistoryEvent
import io.temporal.client.WorkflowClient
import io.temporal.client.WorkflowOptions
import io.temporal.client.WorkflowStub
import io.temporal.testing.TestWorkflowEnvironment
import io.temporal.worker.WorkerFactory
import io.temporal.worker.WorkerOptions
import io.temporal.workflow.Workflow
import io.temporal.workflow.WorkflowInterface
import io.temporal.workflow.WorkflowMethod
import java.time.Duration
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

// Shared by the lesson 5 Temporal demos: a small order workflow, three versions of it, fake systems and helpers.

const val QUEUE = "orders"

@WorkflowInterface
interface OrderWorkflow {
    @WorkflowMethod
    fun process(orderId: String, amountCents: Long): String
}

@ActivityInterface
interface Steps {
    fun checkFraud(orderId: String, amountCents: Long): Boolean
    fun charge(key: String, orderId: String, amountCents: Long): String
    fun reserve(key: String, orderId: String): String
    fun ship(key: String, orderId: String): String
}

/** A bank that can honour idempotency keys or ignore them, and counts the charges it made. */
class FakeBank(private val honorKeys: Boolean) {
    private val seen = ConcurrentHashMap<String, String>()
    val charges = AtomicInteger()
    fun charge(key: String): String {
        if (honorKeys) seen[key]?.let { return it }
        val id = "ch_${charges.incrementAndGet()}"
        seen[key] = id
        return id
    }
}

/** The activities. [crashAfterCharge] makes the first charge attempt fail after the money moved. */
class StepsImpl(private val bank: FakeBank, private val crashAfterCharge: Boolean = false) : Steps {
    val runs = ConcurrentHashMap<String, AtomicInteger>()
    private fun count(step: String) = runs.computeIfAbsent(step) { AtomicInteger() }.incrementAndGet()
    fun runs(step: String) = runs[step]?.get() ?: 0

    override fun checkFraud(orderId: String, amountCents: Long): Boolean { count("checkFraud"); return amountCents < 100_000 }
    override fun charge(key: String, orderId: String, amountCents: Long): String {
        count("charge")
        val id = bank.charge(key)
        if (crashAfterCharge && Activity.getExecutionContext().info.attempt == 1) {
            throw IllegalStateException("worker died after charging, before reporting back")
        }
        return id
    }
    override fun reserve(key: String, orderId: String): String { count("reserve"); return "res_$orderId" }
    override fun ship(key: String, orderId: String): String { count("ship"); return "trk_$orderId" }
}

private fun stepsStub(): Steps = Workflow.newActivityStub(
    Steps::class.java,
    ActivityOptions {
        setStartToCloseTimeout(Duration.ofSeconds(10))
        setRetryOptions { setInitialInterval(Duration.ofSeconds(1)) }
    },
)

/** Version 1: charge, reserve, wait for the courier, ship. */
class OrderV1 : OrderWorkflow {
    private val steps = stepsStub()
    override fun process(orderId: String, amountCents: Long): String {
        val id = Workflow.getInfo().workflowId
        steps.charge("$id/charge", orderId, amountCents)
        steps.reserve("$id/reserve", orderId)
        Workflow.sleep(Duration.ofHours(24))
        steps.ship("$id/ship", orderId)
        return "SHIPPED"
    }
}

/** Version 2 done wrong: a fraud check put in front of the charge, for every run, old or new. */
class OrderV2Naive : OrderWorkflow {
    private val steps = stepsStub()
    override fun process(orderId: String, amountCents: Long): String {
        if (!steps.checkFraud(orderId, amountCents)) return "REJECTED"
        return OrderV1Steps.rest(steps, orderId, amountCents)
    }
}

/** Version 2 done right: the fraud check only for runs that reach this point on the new code. */
class OrderV2 : OrderWorkflow {
    private val steps = stepsStub()
    override fun process(orderId: String, amountCents: Long): String {
        val version = Workflow.getVersion("fraud-check", Workflow.DEFAULT_VERSION, 1)
        if (version == 1 && !steps.checkFraud(orderId, amountCents)) return "REJECTED"
        return OrderV1Steps.rest(steps, orderId, amountCents)
    }
}

object OrderV1Steps {
    fun rest(steps: Steps, orderId: String, amountCents: Long): String {
        val id = Workflow.getInfo().workflowId
        steps.charge("$id/charge", orderId, amountCents)
        steps.reserve("$id/reserve", orderId)
        Workflow.sleep(Duration.ofHours(24))
        steps.ship("$id/ship", orderId)
        return "SHIPPED"
    }
}

/** A worker in its own WorkerFactory: stopping the factory is the demo's "kill -9". */
class DemoWorker(val name: String, val factory: WorkerFactory, val steps: StepsImpl) {
    fun kill() {
        factory.shutdownNow()
        factory.awaitTermination(5, TimeUnit.SECONDS)
    }
}

fun startWorker(client: WorkflowClient, name: String, workflow: Class<out OrderWorkflow>, steps: StepsImpl): DemoWorker {
    val factory = WorkerFactory.newInstance(client)
    val options = WorkerOptions.newBuilder()
        .setIdentity(name)
        // the in-memory test server can't move work off a dead worker's sticky queue; a real server does after 5 s
        .setStickyQueueScheduleToStartTimeout(Duration.ZERO)
        .build()
    val worker = factory.newWorker(QUEUE, options)
    worker.registerWorkflowImplementationTypes(workflow)
    worker.registerActivitiesImplementations(steps)
    factory.start()
    return DemoWorker(name, factory, steps)
}

fun startOrder(client: WorkflowClient, orderId: String, amountCents: Long = 4_000): WorkflowStub {
    val stub = client.newUntypedWorkflowStub(
        "OrderWorkflow",
        WorkflowOptions.newBuilder().setWorkflowId(orderId).setTaskQueue(QUEUE).build(),
    )
    stub.start(orderId, amountCents)
    return stub
}

fun waitForTimer(client: WorkflowClient, orderId: String) {
    while (client.fetchHistory(orderId).events.none { it.hasTimerStartedEventAttributes() }) Thread.sleep(20)
}

/** One line per event: id, type, and for the events that have them, the activity, the attempt or the worker. */
fun describe(e: HistoryEvent): String {
    val type = e.eventType.name.removePrefix("EVENT_TYPE_")
    val detail = when {
        e.hasActivityTaskScheduledEventAttributes() -> e.activityTaskScheduledEventAttributes.activityType.name
        e.hasActivityTaskStartedEventAttributes() ->
            "attempt ${e.activityTaskStartedEventAttributes.attempt} on ${e.activityTaskStartedEventAttributes.identity}"
        e.hasWorkflowTaskStartedEventAttributes() -> "on ${e.workflowTaskStartedEventAttributes.identity}"
        e.hasMarkerRecordedEventAttributes() -> e.markerRecordedEventAttributes.markerName
        e.hasTimerStartedEventAttributes() -> "fires in ${e.timerStartedEventAttributes.startToFireTimeout.seconds / 3600} h"
        else -> ""
    }
    return "%3d  %-28s %s".format(e.eventId, type, detail).trimEnd()
}

fun newEnv(): TestWorkflowEnvironment = TestWorkflowEnvironment.newInstance()

/** Keeps the SDK's own warnings (a failed activity attempt, a test server without heartbeats) out of the output. */
fun quiet() {
    System.setProperty("org.slf4j.simpleLogger.log.io.temporal", "error")
}
