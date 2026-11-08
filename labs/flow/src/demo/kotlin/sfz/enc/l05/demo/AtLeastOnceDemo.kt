package sfz.enc.l05.demo

/**
 * The first charge attempt moves the money and then dies before reporting back. Temporal retries it.
 * Run twice: against a bank that ignores idempotency keys, and against one that honours them.
 */
fun main() {
    quiet()
    for (honorKeys in listOf(false, true)) {
        newEnv().use { env ->
            val bank = FakeBank(honorKeys)
            val worker = startWorker(env.workflowClient, "worker-1", OrderV1::class.java, StepsImpl(bank, crashAfterCharge = true))
            val result = startOrder(env.workflowClient, "order-7").getResult(String::class.java)
            println("bank honours keys=$honorKeys: $result, charge activity ran ${worker.steps.runs("charge")}x, card charged ${bank.charges.get()}x")
            if (!honorKeys) {
                env.workflowClient.fetchHistory("order-7").events
                    .filter { it.hasActivityTaskScheduledEventAttributes() || it.hasActivityTaskStartedEventAttributes() || it.hasActivityTaskCompletedEventAttributes() }
                    .take(3)
                    .forEach { println("    " + describe(it)) }
            }
            worker.kill()
        }
    }
}
