package sfz.net.l12

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.net.support.ManualClock

/**
 * The capstone incident. The load balancer forgets idle connections after 350 s (a cloud network
 * load balancer's default) and resets them on their next use. Authorizations come in a burst, then
 * the service is quiet for 400 s.
 */
class IdleMismatchTest {
    private val clock = ManualClock()
    private val lb = FakeLb(idleTimeoutMs = 350_000, clock = clock)
    private val sleeps = mutableListOf<Long>()

    private fun caller(poolIdleMs: Long): Caller {
        val pool = ConnectionPool(maxSize = 20, idleTimeoutMs = poolIdleMs, maxLifetimeMs = 3_600_000, clock = clock, connect = lb::connect)
        val policy = RetryPolicy(maxAttempts = 3, budget = RetryBudget(), random = { 0.5 })
        return Caller(pool, policy) { ms -> sleeps += ms; clock.advance(ms) }
    }

    @Test
    fun `a pool that keeps idle connections longer than the LB gets a reset, and the POST fails`() {
        val c = caller(poolIdleMs = 600_000)
        assertThat(c.call(Request("POST", "/authorize")).outcome).isEqualTo(Outcome.Status(200))
        clock.advanceSeconds(400)
        val r = c.call(Request("POST", "/authorize"))
        assertThat(r.outcome).isEqualTo(Outcome.Reset)
        assertThat(r.attempts).`as`("a bare POST may not be sent twice").isEqualTo(1)
        assertThat(lb.resets).containsExactly(1)
    }

    @Test
    fun `the same reset on a GET or a keyed POST is retried on a fresh connection`() {
        val c = caller(poolIdleMs = 600_000)
        c.call(Request("GET", "/payments/42"))
        clock.advanceSeconds(400)
        val r = c.call(Request("POST", "/authorize", idempotencyKey = "ord-7731"))
        assertThat(r.outcome).isEqualTo(Outcome.Status(200))
        assertThat(r.log).hasSize(2)
        assertThat(r.log[0]).contains("connection 1 (reused)").contains("Reset")
        assertThat(r.log[1]).contains("connection 2 (new)")
        assertThat(sleeps).`as`("full jitter: half of the 100 ms ceiling").containsExactly(50L)
    }

    @Test
    fun `a pool idle timeout below the LB's means the reset never happens`() {
        val c = caller(poolIdleMs = 300_000)
        c.call(Request("POST", "/authorize"))
        clock.advanceSeconds(400)
        val r = c.call(Request("POST", "/authorize"))
        assertThat(r.outcome).isEqualTo(Outcome.Status(200))
        assertThat(r.log).containsExactly("attempt 1 on connection 2 (new): Status(code=200)")
        assertThat(lb.resets).isEmpty()
        assertThat(lb.closedByClient).`as`("the pool closed it first").containsExactly(1)
    }
}
