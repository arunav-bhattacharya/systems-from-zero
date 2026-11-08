package sfz.enc.l05.demo

/**
 * Starts an order on worker-1, kills worker-1 while the order waits 24 hours for the courier,
 * then starts worker-2, which finishes the order from the history alone.
 */
fun main() {
    quiet()
    newEnv().use { env ->
        val client = env.workflowClient
        val bank = FakeBank(honorKeys = true)
        val first = startWorker(client, "worker-1", OrderV1::class.java, StepsImpl(bank))
        val order = startOrder(client, "order-42")
        waitForTimer(client, "order-42")
        first.kill()
        println("worker-1 killed while order-42 sleeps; it ran charge=${first.steps.runs("charge")} reserve=${first.steps.runs("reserve")}")

        val second = startWorker(client, "worker-2", OrderV1::class.java, StepsImpl(bank))
        println("result: ${order.getResult(String::class.java)}") // the test server skips the 24 hours
        println("worker-2 ran charge=${second.steps.runs("charge")} reserve=${second.steps.runs("reserve")} ship=${second.steps.runs("ship")}")
        println("cards charged: ${bank.charges.get()}")
        println()
        println("the event history of order-42:")
        client.fetchHistory("order-42").events.forEach { println(describe(it)) }
        second.kill()
    }
}
