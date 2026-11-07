package sfz.net.l12

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class RetryPolicyTest {
    private val get = Request("GET", "/payments/42")
    private val post = Request("POST", "/authorize")
    private val keyedPost = Request("POST", "/authorize", idempotencyKey = "ord-7731")

    private fun policy(r: Double = 0.5, budget: RetryBudget = RetryBudget()) = RetryPolicy(maxAttempts = 3, baseMs = 100, capMs = 2_000, budget = budget, random = { r })

    @Test
    fun `GET, PUT and DELETE are idempotent, a POST only with an idempotency key`() {
        val p = policy()
        assertThat(listOf("GET", "HEAD", "PUT", "DELETE", "OPTIONS").map { p.isIdempotent(Request(it, "/x")) }).containsOnly(true)
        assertThat(p.isIdempotent(post)).isFalse()
        assertThat(p.isIdempotent(keyedPost)).isTrue()
        assertThat(p.isIdempotent(Request("PATCH", "/x"))).isFalse()
    }

    @Test
    fun `a connect failure is always safe to retry, because nothing was sent`() {
        val p = policy()
        assertThat(p.mayRetry(post, Outcome.ConnectRefused)).isTrue()
        assertThat(p.mayRetry(post, Outcome.ConnectTimeout)).isTrue()
    }

    @Test
    fun `after the request went out, only idempotent requests are retried`() {
        val p = policy()
        for (o in listOf(Outcome.Reset, Outcome.ReadTimeout, Outcome.Status(503), Outcome.Status(502), Outcome.Status(504), Outcome.Status(429))) {
            assertThat(p.mayRetry(get, o)).`as`("GET after $o").isTrue()
            assertThat(p.mayRetry(keyedPost, o)).`as`("POST with a key after $o").isTrue()
            assertThat(p.mayRetry(post, o)).`as`("a bare POST after $o could charge twice").isFalse()
        }
    }

    @Test
    fun `the same request gets the same 4xx or 500 again, so it isn't retried`() {
        val p = policy()
        for (code in listOf(400, 401, 404, 409, 500, 501)) assertThat(p.mayRetry(get, Outcome.Status(code))).`as`("$code").isFalse()
    }

    @Test
    fun `backoff doubles up to the cap, and full jitter picks a point below it`() {
        val top = policy(r = 0.999_999)
        assertThat((1..6).map(top::backoffMs)).containsExactly(99, 199, 399, 799, 1599, 1999)
        assertThat(top.backoffMs(40)).`as`("still capped, no overflow").isEqualTo(1999)
        assertThat(policy(r = 0.5).backoffMs(3)).isEqualTo(200)
        assertThat(policy(r = 0.0).backoffMs(5)).`as`("full jitter may retry at once").isEqualTo(0)
    }

    @Test
    fun `decide waits, then stops at maxAttempts`() {
        val p = policy(r = 0.5)
        assertThat(p.decide(get, Outcome.Status(503), 1)).isEqualTo(Decision.RetryAfter(50))
        assertThat(p.decide(get, Outcome.Status(503), 2)).isEqualTo(Decision.RetryAfter(100))
        assertThat(p.decide(get, Outcome.Status(503), 3)).isInstanceOf(Decision.GiveUp::class.java)
        assertThat(p.decide(post, Outcome.Reset, 1)).isInstanceOf(Decision.GiveUp::class.java)
    }

    @Test
    fun `the budget allows one retry per ten calls once its reserve is spent`() {
        val budget = RetryBudget(ratio = 0.1, maxTokens = 10.0)
        assertThat((1..12).map { budget.tryRetry() }.count { it }).`as`("the starting reserve").isEqualTo(10)
        repeat(9) { budget.onRequest() }
        assertThat(budget.tryRetry()).`as`("0.9 tokens").isFalse()
        budget.onRequest()
        assertThat(budget.tryRetry()).`as`("1.0 token after ten calls").isTrue()
        repeat(500) { budget.onRequest() }
        assertThat(budget.tokens).`as`("never above the maximum").isEqualTo(10.0)
    }

    @Test
    fun `an empty budget stops retries, and a refused retry costs no token`() {
        val budget = RetryBudget(ratio = 0.1, maxTokens = 1.0)
        val p = policy(budget = budget)
        assertThat(p.decide(post, Outcome.Reset, 1)).`as`("refused before the budget").isInstanceOf(Decision.GiveUp::class.java)
        assertThat(budget.tokens).isEqualTo(1.0)
        assertThat(p.decide(get, Outcome.Status(503), 1)).isInstanceOf(Decision.RetryAfter::class.java)
        assertThat(p.decide(get, Outcome.Status(503), 1)).isEqualTo(Decision.GiveUp("retry budget empty"))
    }
}
