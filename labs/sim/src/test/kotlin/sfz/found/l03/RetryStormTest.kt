package sfz.found.l03

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.data.Offset
import org.junit.jupiter.api.Test

/**
 * 800 new requests a second against a server that can finish 1,000. From t=10 s to t=15 s a
 * slow dependency cuts capacity to 400 a second. Clients give up on an attempt after 200 ms.
 */
class RetryStormTest {
    private val config = StormConfig()

    @Test
    fun `the retry budget earns a tenth of a token per request and spends one per retry`() {
        val budget = RetryBudget(ratio = 0.1, maxTokens = 10.0, maxAttempts = 4)
        assertThat(budget.allowRetry(1)).isFalse()                     // an empty bucket: no retry
        repeat(25) { budget.onRequest() }
        assertThat(budget.available).isCloseTo(2.5, Offset.offset(1e-9))
        assertThat(budget.allowRetry(1)).isTrue()
        assertThat(budget.allowRetry(2)).isTrue()
        assertThat(budget.allowRetry(1)).isFalse()                     // 0.5 left: not a whole token
        assertThat(budget.available).isCloseTo(0.5, Offset.offset(1e-9))
    }

    @Test
    fun `the bucket never holds more than its maximum`() {
        val budget = RetryBudget(ratio = 0.1, maxTokens = 10.0)
        repeat(1_000) { budget.onRequest() }
        assertThat(budget.available).isCloseTo(10.0, Offset.offset(1e-9))
    }

    @Test
    fun `the budget still stops at the last attempt`() {
        val budget = RetryBudget(ratio = 0.1, maxTokens = 10.0, maxAttempts = 4)
        repeat(100) { budget.onRequest() }
        assertThat(budget.allowRetry(3)).isTrue()
        assertThat(budget.allowRetry(4)).isFalse()
    }

    @Test
    fun `with no trigger every request gets an answer in time`() {
        val quiet = config.copy(triggerCapacity = config.capacityPerSecond)
        val run = simulateStorm(quiet, RetryUpTo(4))
        assertThat(run.sumOf { it.goodput }).isEqualTo(run.sumOf { it.newRequests })
    }

    @Test
    fun `plain retries keep the service down long after the trigger has gone`() {
        val run = simulateStorm(config, RetryUpTo(4))
        assertThat(recoveredAt(run, config)).isNull()
        val late = run.filter { it.t >= 30 }
        assertThat(late.sumOf { it.goodput }).isZero()                               // no useful work at all
        assertThat(late.all { it.attempts >= 3 * config.capacityPerSecond }).isTrue() // four attempts per request
    }

    @Test
    fun `backoff with jitter spreads the retries out but does not end the storm`() {
        val run = simulateStorm(config, BackoffRetry(4))
        assertThat(recoveredAt(run, config)).isNull()
    }

    @Test
    fun `a retry budget caps the extra load, so the service recovers once the backlog drains`() {
        val run = simulateStorm(config, RetryBudget())
        assertThat(recoveredAt(run, config)).isNotNull().isLessThanOrEqualTo(40)
        for (s in run) assertThat(s.attempts).`as`("t=${s.t}").isLessThanOrEqualTo((s.newRequests * 1.1).toInt() + 10)
    }

    @Test
    fun `shedding work nobody waits for gets it back as soon as the trigger ends`() {
        val run = simulateStorm(config.copy(shedExpired = true), RetryUpTo(4))
        assertThat(recoveredAt(run, config)).isEqualTo(config.triggerToSec)
        assertThat(run.sumOf { it.wasted }).isZero()
    }
}
