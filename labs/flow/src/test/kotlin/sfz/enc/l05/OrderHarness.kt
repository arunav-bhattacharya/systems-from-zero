package sfz.enc.l05

import io.temporal.api.enums.v1.EventType
import io.temporal.client.WorkflowClient
import io.temporal.client.WorkflowOptions
import io.temporal.client.WorkflowStub
import io.temporal.testing.TestWorkflowEnvironment
import io.temporal.worker.NonDeterministicException
import io.temporal.worker.WorkerFactory
import io.temporal.worker.WorkerOptions
import io.temporal.worker.WorkflowImplementationOptions
import java.time.Duration
import java.util.concurrent.TimeUnit

/**
 * One in-process Temporal test server (no Docker) plus workers you can start and stop.
 * Each worker gets its own WorkerFactory, so stopping one is like killing that worker process.
 */
class OrderHarness(val world: World = World()) : AutoCloseable {
    val env: TestWorkflowEnvironment = TestWorkflowEnvironment.newInstance()
    val client: WorkflowClient = env.workflowClient
    private val factories = mutableListOf<WorkerFactory>()

    // In the tests, a TODO stub or a non-determinism error fails the workflow at once. In production both
    // fail only the workflow task, which Temporal retries until you deploy a fix.
    private val failFast = WorkflowImplementationOptions.newBuilder()
        .setFailWorkflowExceptionTypes(NotImplementedError::class.java, NonDeterministicException::class.java)
        .build()

    class RunningWorker(val factory: WorkerFactory, val activities: OrderActivitiesImpl) {
        /** Stops this worker for good and throws away the workflows it had in memory, like a process that died. */
        fun stop() {
            factory.shutdownNow()
            factory.awaitTermination(5, TimeUnit.SECONDS)
        }
    }

    fun startWorker(
        workflowClass: Class<out OrderWorkflow> = OrderWorkflowImpl::class.java,
        crashAfter: Set<String> = emptySet(),
    ): RunningWorker {
        val factory = WorkerFactory.newInstance(client)
        val options = WorkerOptions.newBuilder()
            // a name per worker, as if each were its own process; the history records which worker ran each task
            .setIdentity("worker-${factories.size + 1}")
            // No sticky queue. A real server moves a task off a dead worker's sticky queue after 5 seconds;
            // the in-memory test server never does, so a stopped worker would strand its workflows.
            .setStickyQueueScheduleToStartTimeout(Duration.ZERO)
            .build()
        val worker = factory.newWorker(TASK_QUEUE, options)
        worker.registerWorkflowImplementationTypes(failFast, workflowClass)
        val activities = OrderActivitiesImpl(world, crashAfter)
        worker.registerActivitiesImplementations(activities)
        factory.start()
        factories += factory
        return RunningWorker(factory, activities)
    }

    /** Starts an order and returns at once, without waiting for it. */
    fun start(orderId: String, amountCents: Long = 4_000, sku: String = "sku-1"): WorkflowStub {
        val options = WorkflowOptions.newBuilder().setWorkflowId(orderId).setTaskQueue(TASK_QUEUE).build()
        val stub = client.newUntypedWorkflowStub("OrderWorkflow", options)
        stub.start(orderId, amountCents, sku)
        return stub
    }

    /** Runs an order to the end. Waiting for the result lets the test server skip the 24-hour timer. */
    fun run(orderId: String, amountCents: Long = 4_000, sku: String = "sku-1"): String =
        start(orderId, amountCents, sku).getResult(String::class.java)

    fun events(workflowId: String): List<EventType> = client.fetchHistory(workflowId).events.map { it.eventType }

    /** Waits (real time) until the workflow's history holds [type], for example its timer starting. */
    fun awaitEvent(workflowId: String, type: EventType) {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(8)
        while (type !in events(workflowId)) {
            check(System.nanoTime() < deadline) { "no $type in the history of $workflowId: ${events(workflowId)}" }
            Thread.sleep(20)
        }
    }

    override fun close() {
        factories.forEach { it.shutdownNow() }
        env.close()
    }
}
