package sfz.dist.l01.demo

/**
 * Lesson dist-01, section 1: six different worlds, one view from the client.
 *
 * The shop sends one authorization with a 2-second timeout and no retry. In each world something
 * different goes wrong. The demo prints what the client knows when its timeout fires, and then what
 * really happened at the issuer.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l01.demo.SilenceDemoKt
 * Optional: -Pargs='3' retries up to 3 attempts with the same key.
 */
fun main(args: Array<String>) {
    val attempts = args.firstOrNull()?.toInt() ?: 1
    val slow = Faults(minDelayMs = 5_000, maxDelayMs = 5_000)
    val worlds = listOf<Pair<String, () -> Run>>(
        "the request is lost" to { one(attempts, requests = Faults(loss = 1.0)) },
        "the request waits 5 s in a queue" to { one(attempts, requests = slow) },
        "the issuer has crashed" to { one(attempts) { it.server.crash() } },
        "the issuer is paused for 5 s" to { one(attempts) { it.server.pauseUntil(5_000) } },
        "the reply is lost" to { one(attempts, replies = Faults(loss = 1.0)) },
        "the reply waits 5 s in a queue" to { one(attempts, replies = slow) },
    )
    println("One payment, pay-1, timeout 2,000 ms, $attempts attempt(s) with the same key")
    println()
    println("%-34s %-26s %-22s %s".format("world", "the client decides", "the issuer charged", "reply after the decision"))
    for ((name, world) in worlds) {
        val run = world()
        val outcome = run.client.outcomes.getValue("pay-1")
        val decided = when (outcome) {
            is Outcome.Approved -> "approved at ${outcome.atMs} ms"
            is Outcome.Unknown -> "unknown at ${outcome.atMs} ms"
        }
        val charged = run.server.charges.joinToString { "once at ${it.atMs} ms" }.ifEmpty { "never" }
        val late = if (run.client.lateReplies > 0) "yes (${run.client.lateReplies})" else "no"
        println("%-34s %-26s %-22s %s".format(name, decided, charged, late))
    }
}

private fun one(attempts: Int, requests: Faults? = null, replies: Faults? = null, setup: (Run) -> Unit = {}) =
    payments(count = 1, timeoutMs = 2_000, maxAttempts = attempts, requests = requests, replies = replies, setup = setup)
