package sfz.kafka.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.kafka.l05.IdempotentLog.Appended
import sfz.kafka.l05.IdempotentLog.Duplicate
import sfz.kafka.l05.IdempotentLog.OutOfOrder

/** The leader's duplicate check for idempotent producers. No broker needed. */
class IdempotentLogTest {
    private val pid = 1000L

    @Test
    fun `batches in sequence are appended at consecutive offsets`() {
        val log = IdempotentLog()
        assertThat(log.append(pid, 0, listOf("p0", "p1", "p2"))).isEqualTo(Appended(0))
        assertThat(log.append(pid, 3, listOf("p3", "p4"))).isEqualTo(Appended(3))
        assertThat(log.records()).containsExactly("p0", "p1", "p2", "p3", "p4")
    }

    @Test
    fun `a new producer must start at sequence 0`() {
        val log = IdempotentLog()
        assertThat(log.append(pid, 5, listOf("p5"))).isEqualTo(OutOfOrder(0))
        assertThat(log.records()).isEmpty()
    }

    @Test
    fun `a retry after a lost acknowledgement is recognised and not written twice`() {
        val log = IdempotentLog()
        log.append(pid, 0, listOf("p0", "p1"))
        log.append(pid, 2, listOf("p2", "p3")) // written, but the response is lost on the way back
        // the producer times out and resends the same batch, with the same sequence numbers
        assertThat(log.append(pid, 2, listOf("p2", "p3"))).isEqualTo(Duplicate(2))
        assertThat(log.records()).containsExactly("p0", "p1", "p2", "p3")
    }

    @Test
    fun `a retry of any of the last five batches is still recognised`() {
        val log = IdempotentLog()
        for (b in 0 until 5) log.append(pid, b * 2, listOf("p${b * 2}", "p${b * 2 + 1}"))
        assertThat(log.append(pid, 0, listOf("p0", "p1"))).isEqualTo(Duplicate(0)) // the oldest of five
        assertThat(log.records()).hasSize(10)
    }

    @Test
    fun `a retry older than five batches can no longer be told apart and is refused`() {
        val log = IdempotentLog()
        for (b in 0 until 6) log.append(pid, b, listOf("p$b"))
        assertThat(log.append(pid, 0, listOf("p0"))).isEqualTo(OutOfOrder(6))
        assertThat(log.records()).hasSize(6)
    }

    @Test
    fun `five batches in flight with the first one lost are refused until it arrives, so order survives`() {
        val log = IdempotentLog()
        // batches 0..4 of one record each are in flight; batch 0 is lost on the way to the leader
        for (s in 1..4) assertThat(log.append(pid, s, listOf("p$s"))).isEqualTo(OutOfOrder(0))
        assertThat(log.records()).isEmpty()
        // the producer resends all five in order
        for (s in 0..4) assertThat(log.append(pid, s, listOf("p$s"))).isEqualTo(Appended(s.toLong()))
        assertThat(log.records()).containsExactly("p0", "p1", "p2", "p3", "p4")
    }

    @Test
    fun `each producer has its own sequence numbers`() {
        val log = IdempotentLog()
        assertThat(log.append(1L, 0, listOf("a0"))).isEqualTo(Appended(0))
        assertThat(log.append(2L, 0, listOf("b0"))).isEqualTo(Appended(1))
        assertThat(log.append(1L, 1, listOf("a1"))).isEqualTo(Appended(2))
        assertThat(log.append(2L, 0, listOf("b0"))).isEqualTo(Duplicate(1))
        assertThat(log.records()).containsExactly("a0", "b0", "a1")
    }
}
