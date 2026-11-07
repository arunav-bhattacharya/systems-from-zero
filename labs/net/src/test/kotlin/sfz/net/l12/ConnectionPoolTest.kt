package sfz.net.l12

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.net.support.ManualClock

class ConnectionPoolTest {
    private val clock = ManualClock()
    private val lb = FakeLb(idleTimeoutMs = 350_000, clock = clock)
    private fun pool(max: Int = 2, idle: Long = 30_000, life: Long = 600_000) = ConnectionPool(max, idle, life, clock, lb::connect)

    @Test
    fun `a released connection is reused, so the handshake happens once`() {
        val pool = pool()
        val first = pool.acquire()
        assertThat(first.reused).isFalse()
        pool.release(first.connection, healthy = true)
        clock.advanceSeconds(5)
        val second = pool.acquire()
        assertThat(second.reused).isTrue()
        assertThat(second.connection.id).isEqualTo(first.connection.id)
        assertThat(lb.opened).isEqualTo(1)
    }

    @Test
    fun `an idle connection past the idle timeout is closed, not reused`() {
        val pool = pool(idle = 30_000)
        val c = pool.acquire().connection
        pool.release(c, healthy = true)
        clock.advanceSeconds(30)
        val next = pool.acquire()
        assertThat(next.reused).isFalse()
        assertThat(lb.closedByClient).containsExactly(c.id)
        assertThat(pool.open).isEqualTo(1)
    }

    @Test
    fun `the most recently released connection goes out first`() {
        val pool = pool()
        val a = pool.acquire().connection
        val b = pool.acquire().connection
        pool.release(a, healthy = true)
        clock.advanceSeconds(1)
        pool.release(b, healthy = true)
        assertThat(pool.idle).isEqualTo(2)
        assertThat(pool.acquire().connection.id).isEqualTo(b.id)
    }

    @Test
    fun `a broken connection is closed when it comes back`() {
        val pool = pool()
        val c = pool.acquire().connection
        pool.release(c, healthy = false)
        assertThat(pool.open).isEqualTo(0)
        assertThat(pool.idle).isEqualTo(0)
        assertThat(lb.closedByClient).containsExactly(c.id)
    }

    @Test
    fun `an old connection is retired even though it is busy every second`() {
        val pool = pool(life = 600_000)
        var ids = mutableSetOf<Int>()
        repeat(700) {
            val lease = pool.acquire()
            ids += lease.connection.id
            pool.release(lease.connection, healthy = true)
            clock.advanceSeconds(1)
        }
        assertThat(ids).`as`("one connection for 600 s, then a new one").containsExactly(1, 2)
    }

    @Test
    fun `a full pool refuses instead of opening more connections`() {
        val pool = pool(max = 2)
        pool.acquire()
        pool.acquire()
        assertThatThrownBy { pool.acquire() }.isInstanceOf(PoolExhausted::class.java)
        assertThat(lb.opened).isEqualTo(2)
    }
}
