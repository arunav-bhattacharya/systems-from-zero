package sfz.net.l12

/**
 * What a payment service's HTTP client does for one call: take a connection from the pool, send,
 * give the connection back, and ask the policy whether to try again. Finished: it only wires your
 * [ConnectionPool] and [RetryPolicy] together. [sleep] waits between attempts (tests pass a fake).
 */
class Caller(private val pool: ConnectionPool, private val policy: RetryPolicy, private val sleep: (Long) -> Unit) {

    /** The final outcome, how many attempts it took, and one line per attempt. */
    data class Result(val outcome: Outcome, val attempts: Int, val log: List<String>)

    fun call(request: Request): Result {
        policy.budget.onRequest()                                    // every call earns the budget a little
        val log = mutableListOf<String>()
        var attempt = 0
        while (true) {
            attempt++
            val lease = pool.acquire()
            val outcome = lease.connection.send(request)
            pool.release(lease.connection, healthy = outcome is Outcome.Status)
            log += "attempt $attempt on connection ${lease.connection.id} (${if (lease.reused) "reused" else "new"}): $outcome"
            if (outcome is Outcome.Status && outcome.code < 500) return Result(outcome, attempt, log)
            when (val d = policy.decide(request, outcome, attempt)) {
                is Decision.GiveUp -> {
                    log += "gave up: ${d.reason}"
                    return Result(outcome, attempt, log)
                }
                is Decision.RetryAfter -> sleep(d.delayMs)
            }
        }
    }
}
