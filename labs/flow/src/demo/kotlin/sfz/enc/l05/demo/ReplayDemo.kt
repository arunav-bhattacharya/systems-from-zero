package sfz.enc.l05.demo

import io.temporal.testing.WorkflowReplayer

/**
 * Records the history of an order that ran on version 1, then replays it against two versions of the new code,
 * the way a CI job replays histories saved from production before a deploy.
 */
fun main() {
    quiet()
    val history = newEnv().use { env ->
        val worker = startWorker(env.workflowClient, "worker-1", OrderV1::class.java, StepsImpl(FakeBank(true)))
        startOrder(env.workflowClient, "order-9").getResult(String::class.java)
        worker.kill()
        env.workflowClient.fetchHistory("order-9")
    }
    println("a version-1 history with ${history.events.size} events")

    for (code in listOf(OrderV2Naive::class.java, OrderV2::class.java)) {
        try {
            WorkflowReplayer.replayWorkflowExecution(history, code)
            println("${code.simpleName}: replays cleanly")
        } catch (e: Exception) {
            // the replayer wraps the error; dig out the NonDeterministicException's own message
            val text = generateSequence<Throwable>(e) { it.cause }.joinToString(" ") { it.message ?: "" }
            println("${code.simpleName}: " + text.substringAfter("error=").substringBefore(" {WorkflowTaskStartedEventId").replace("\n", ""))
        }
    }
}
