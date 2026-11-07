package sfz.net.l12

import kotlin.math.min

/** What to do after a failed attempt. */
sealed interface Decision {
    data class RetryAfter(val delayMs: Long) : Decision
    data class GiveUp(val reason: String) : Decision
}

/**
 * A retry budget: retries may add at most about [ratio] extra load. It holds tokens, at most
 * [maxTokens], and starts full. Every call adds [ratio] tokens; every retry spends one whole token.
 * With 0.1, once the starting tokens are spent, you get one retry per ten calls.
 */
class RetryBudget(private val ratio: Double = 0.1, private val maxTokens: Double = 10.0) {

    /** Tokens left now. */
    val tokens: Double
        get() = TODO("return the current token count")

    /** One call was made: add [ratio] tokens, never above [maxTokens]. */
    fun onRequest() {
        TODO("tokens = min(maxTokens, tokens + ratio)")
    }

    /**
     * Spends one token and returns true, or returns false if less than one token is left. Mind the
     * floating point: ten additions of 0.1 make 0.9999999999999999, so allow a little slack (1e-9).
     */
    fun tryRetry(): Boolean {
        TODO("spend a whole token if there is one")
    }
}

/**
 * When a payment client may try again, and how long it waits first.
 *
 * [random] returns a number in [0, 1); tests pass a fixed one.
 */
class RetryPolicy(
    val maxAttempts: Int = 3,
    private val baseMs: Long = 100,
    private val capMs: Long = 2_000,
    val budget: RetryBudget = RetryBudget(),
    private val random: () -> Double = Math::random,
) {
    /**
     * Idempotent: sending it twice has the same effect as sending it once. RFC 9110 says GET, HEAD,
     * OPTIONS, TRACE, PUT and DELETE are. A POST is only if it carries an idempotency key.
     */
    fun isIdempotent(request: Request): Boolean {
        TODO("the RFC 9110 methods, or a POST with an idempotency key")
    }

    /**
     * Is another attempt both safe and worth it?
     * - ConnectRefused, ConnectTimeout: the request never left, so yes, whatever the method.
     * - Reset, ReadTimeout: the server may have acted on it: only if idempotent.
     * - Status 429, 502, 503, 504 (overloaded, or a proxy found no healthy backend): only if idempotent.
     * - Any other status (4xx, 500): no. Sending the same request again gets the same answer.
     */
    fun mayRetry(request: Request, outcome: Outcome): Boolean {
        TODO("never sent: yes; maybe acted on: only idempotent; 429/502/503/504: only idempotent; else no")
    }

    /**
     * Capped exponential backoff with full jitter, for the [retry]th retry (1 for the first):
     * a random wait between 0 and `min(capMs, baseMs * 2^(retry - 1))`, as a whole number of ms.
     */
    fun backoffMs(retry: Int): Long {
        TODO("random() * min(cap, base * 2^(retry - 1))")
    }

    /**
     * After [attempt] attempts (1 after the first) ended with [outcome]: give up if [maxAttempts]
     * are used, or if [mayRetry] says no, or if the budget has no token; otherwise wait [backoffMs].
     * Check in that order, so a refused retry doesn't spend a token.
     */
    fun decide(request: Request, outcome: Outcome, attempt: Int): Decision {
        TODO("attempts, then mayRetry, then the budget, then RetryAfter(backoffMs(attempt))")
    }
}
