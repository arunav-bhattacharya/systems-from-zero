package sfz.kafka.l12

import org.apache.kafka.clients.consumer.AcknowledgeType.ACCEPT
import org.apache.kafka.clients.consumer.AcknowledgeType.REJECT
import org.apache.kafka.clients.consumer.AcknowledgeType.RELEASE
import org.apache.kafka.clients.consumer.AcknowledgeType.RENEW
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.kafka.l12.SharePartition.Delivery
import sfz.kafka.l12.SharePartition.State

/** The share-partition model, with the broker's defaults: 5 deliveries, a 30-second lock. Time is in milliseconds. */
class SharePartitionTest {
    private fun partition(records: Int, maxLocks: Int = 2000) = SharePartition(5, 30_000, maxLocks).also { it.append(records) }

    private fun List<Delivery>.offsets() = map { it.offset() }

    @Test
    fun `three consumers share one partition, and each record goes to one of them`() {
        val p = partition(6)
        assertThat(p.acquire("c1", 2, 0).offsets()).containsExactly(0L, 1L)
        assertThat(p.acquire("c2", 2, 0).offsets()).containsExactly(2L, 3L)
        assertThat(p.acquire("c3", 2, 0).offsets()).containsExactly(4L, 5L)
        assertThat(p.acquire("c1", 2, 0)).isEmpty()   // everything is locked by someone
        assertThat(p.state(3)).isEqualTo(State.ACQUIRED)
    }

    @Test
    fun `ACCEPT finishes a record, and the start offset moves past finished records only`() {
        val p = partition(4)
        p.acquire("c1", 2, 0)
        p.acquire("c2", 2, 0)
        p.acknowledge("c2", 2, ACCEPT, 10)
        assertThat(p.startOffset()).isEqualTo(0)          // 0 and 1 are still in flight
        p.acknowledge("c1", 0, ACCEPT, 20)
        p.acknowledge("c1", 1, ACCEPT, 20)
        assertThat(p.state(1)).isEqualTo(State.ACKNOWLEDGED)
        assertThat(p.startOffset()).isEqualTo(3)          // 0, 1, 2 done; 3 is not
    }

    @Test
    fun `RELEASE hands the record out again, to anyone, with a higher delivery count`() {
        val p = partition(3)
        assertThat(p.acquire("c1", 1, 0)).containsExactly(Delivery(0, 1))
        p.acknowledge("c1", 0, RELEASE, 100)
        assertThat(p.state(0)).isEqualTo(State.AVAILABLE)
        assertThat(p.acquire("c2", 1, 200)).containsExactly(Delivery(0, 2))
    }

    @Test
    fun `after the fifth delivery a release archives the record`() {
        val p = partition(2)
        val counts = mutableListOf<Int>()
        for (attempt in 1..5) {
            val d = p.acquire("c1", 1, attempt * 1_000L).single()
            counts += d.deliveryCount()
            p.acknowledge("c1", d.offset(), RELEASE, attempt * 1_000L)
        }
        assertThat(counts).containsExactly(1, 2, 3, 4, 5)
        assertThat(p.state(0)).isEqualTo(State.ARCHIVED)
        assertThat(p.acquire("c1", 1, 10_000)).containsExactly(Delivery(1, 1))   // the next record, never 0 again
        assertThat(p.startOffset()).isEqualTo(1)
    }

    @Test
    fun `an expired lock frees the record for another consumer, and the old holder's acknowledgement is refused`() {
        val p = partition(2)
        p.acquire("c1", 2, 0)                                          // c1 freezes, holding 0 and 1
        assertThat(p.acquire("c2", 2, 29_999)).isEmpty()                // still locked
        assertThat(p.acquire("c2", 2, 30_000)).containsExactly(Delivery(0, 2), Delivery(1, 2))
        assertThatThrownBy { p.acknowledge("c1", 0, ACCEPT, 30_500) }.isInstanceOf(IllegalStateException::class.java)
        p.acknowledge("c2", 0, ACCEPT, 30_500)
        assertThat(p.state(0)).isEqualTo(State.ACKNOWLEDGED)
    }

    @Test
    fun `a lock that runs out on the last delivery archives the record`() {
        val p = partition(1)
        for (attempt in 0 until 5) assertThat(p.acquire("c1", 1, attempt * 30_000L).single().deliveryCount()).isEqualTo(attempt + 1)
        assertThat(p.acquire("c1", 1, 150_000)).isEmpty()
        assertThat(p.state(0)).isEqualTo(State.ARCHIVED)
    }

    @Test
    fun `RENEW keeps the lock, and REJECT archives at once`() {
        val p = partition(2)
        p.acquire("c1", 2, 0)
        p.acknowledge("c1", 0, RENEW, 25_000)                          // a slow record: more time, please
        assertThat(p.acquire("c2", 2, 40_000).offsets()).containsExactly(1L)   // 1's lock ran out, 0's didn't
        p.acknowledge("c1", 0, ACCEPT, 54_000)
        assertThat(p.deliveryCount(0)).isEqualTo(1)
        p.acknowledge("c2", 1, REJECT, 54_000)
        assertThat(p.state(1)).isEqualTo(State.ARCHIVED)
        assertThat(p.startOffset()).isEqualTo(2)
    }

    @Test
    fun `no more than maxRecordLocks records are in flight at once`() {
        val p = partition(5, maxLocks = 3)
        assertThat(p.acquire("c1", 2, 0).offsets()).containsExactly(0L, 1L)
        assertThat(p.acquire("c2", 2, 0).offsets()).containsExactly(2L)      // the third lock is the last
        assertThat(p.acquire("c3", 2, 0)).isEmpty()
        p.acknowledge("c1", 0, ACCEPT, 10)
        assertThat(p.acquire("c3", 2, 10).offsets()).containsExactly(3L)
    }
}
