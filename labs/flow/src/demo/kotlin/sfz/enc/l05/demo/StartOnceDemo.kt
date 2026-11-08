package sfz.enc.l05.demo

import io.temporal.api.enums.v1.WorkflowIdReusePolicy
import io.temporal.client.WorkflowClient
import io.temporal.client.WorkflowExecutionAlreadyStarted
import io.temporal.client.WorkflowOptions

/**
 * A Kafka consumer starts one order workflow per "order placed" event. The broker may deliver an event twice.
 * The workflow id, built from the order id, is what makes the second start harmless.
 */

/** Starts the order unless it was already started; returns true if this call started it. */
fun startOrderOnce(client: WorkflowClient, orderId: String, amountCents: Long): Boolean {
    val options = WorkflowOptions.newBuilder()
        .setWorkflowId("order-$orderId") // the business key, never a random UUID
        .setTaskQueue(QUEUE)
        // a closed run keeps the id taken until the history leaves retention
        .setWorkflowIdReusePolicy(WorkflowIdReusePolicy.WORKFLOW_ID_REUSE_POLICY_REJECT_DUPLICATE)
        .build()
    return try {
        client.newUntypedWorkflowStub("OrderWorkflow", options).start(orderId, amountCents)
        true
    } catch (e: WorkflowExecutionAlreadyStarted) {
        false // a duplicate delivery: nothing to do, acknowledge the event
    }
}

fun main() {
    quiet()
    newEnv().use { env ->
        val client = env.workflowClient
        val bank = FakeBank(honorKeys = true)
        val worker = startWorker(client, "worker-1", OrderV1::class.java, StepsImpl(bank))
        println("first delivery started a run:  ${startOrderOnce(client, "42", 4_000)}")
        println("second delivery started a run: ${startOrderOnce(client, "42", 4_000)}")
        client.newUntypedWorkflowStub("order-42").getResult(String::class.java)
        println("after the run closed, a third:  ${startOrderOnce(client, "42", 4_000)}")
        println("cards charged: ${bank.charges.get()}")
        worker.kill()
    }
}
