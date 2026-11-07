package sfz.net.l12

import kotlin.math.min

sealed interface Decision {
    data class RetryAfter(val delayMs: Long) : Decision
    data class GiveUp(val reason: String) : Decision
}

class RetryBudget(private val ratio: Double = 0.1, private val maxTokens: Double = 10.0) {
    private var left = maxTokens                                       // a small reserve for quiet periods

    val tokens: Double
        get() = left

    fun onRequest() {
        left = min(maxTokens, left + ratio)
    }

    fun tryRetry(): Boolean {
        if (left < 1.0 - 1e-9) return false                            // the storm stops here (1e-9: see the KDoc)
        left = maxOf(0.0, left - 1.0)
        return true
    }
}

class RetryPolicy(
    val maxAttempts: Int = 3,
    private val baseMs: Long = 100,
    private val capMs: Long = 2_000,
    val budget: RetryBudget = RetryBudget(),
    private val random: () -> Double = Math::random,
) {
    private val idempotentMethods = setOf("GET", "HEAD", "OPTIONS", "TRACE", "PUT", "DELETE")

    fun isIdempotent(request: Request): Boolean =
        request.method.uppercase() in idempotentMethods ||
            (request.method.uppercase() == "POST" && request.idempotencyKey != null)

    fun mayRetry(request: Request, outcome: Outcome): Boolean = when (outcome) {
        Outcome.ConnectRefused, Outcome.ConnectTimeout -> true        // nothing was sent
        Outcome.Reset, Outcome.ReadTimeout -> isIdempotent(request)    // it may have been acted on
        is Outcome.Status -> outcome.code in setOf(429, 502, 503, 504) && isIdempotent(request)
    }

    fun backoffMs(retry: Int): Long {
        val ceiling = min(capMs, baseMs shl (retry - 1).coerceAtMost(30))   // 100, 200, 400 ... capped
        return (random() * ceiling).toLong()                                 // full jitter: anywhere below
    }

    fun decide(request: Request, outcome: Outcome, attempt: Int): Decision = when {
        attempt >= maxAttempts -> Decision.GiveUp("used all $maxAttempts attempts")
        !mayRetry(request, outcome) -> Decision.GiveUp("not safe or not useful to retry: ${request.method} after $outcome")
        !budget.tryRetry() -> Decision.GiveUp("retry budget empty")
        else -> Decision.RetryAfter(backoffMs(attempt))
    }
}
