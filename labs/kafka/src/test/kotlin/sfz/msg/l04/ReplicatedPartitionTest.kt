package sfz.msg.l04

import org.apache.kafka.common.errors.NotEnoughReplicasException
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.msg.l04.ReplicatedPartition.Acks

/**
 * Leader 1, followers 2 and 3, replication factor 3, replica.lag.time.max.ms = 30 s.
 * Time is in milliseconds and starts at 0. No broker needed.
 */
class ReplicatedPartitionTest {
    private val lag = 30_000L

    private fun partition(minIsr: Int = 2) = ReplicatedPartition(1, listOf(1, 2, 3), minIsr, lag, 0)

    @Test
    fun `a new partition has every replica in the ISR and a high watermark of 0`() {
        val p = partition()
        assertThat(p.isr()).containsExactly(1, 2, 3)
        assertThat(p.highWatermark()).isEqualTo(0)
    }

    @Test
    fun `append moves the leader's log end offset and returns the last offset written`() {
        val p = partition()
        assertThat(p.append(5, Acks.ALL)).isEqualTo(4)
        assertThat(p.append(3, Acks.ALL)).isEqualTo(7)
        assertThat(p.logEndOffset(1)).isEqualTo(8)
        assertThat(p.highWatermark()).isEqualTo(0) // the followers have nothing yet
    }

    @Test
    fun `the high watermark is the smallest log end offset in the ISR`() {
        val p = partition()
        p.append(5, Acks.ALL)
        p.fetch(2, 5, 100)
        assertThat(p.highWatermark()).isEqualTo(0) // follower 3 has nothing
        p.fetch(3, 3, 100)
        assertThat(p.highWatermark()).isEqualTo(3)
        p.fetch(3, 5, 200)
        assertThat(p.highWatermark()).isEqualTo(5)
    }

    @Test
    fun `a record is committed, and visible to consumers, only below the high watermark`() {
        val p = partition()
        p.append(5, Acks.ALL)
        p.fetch(2, 5, 100)
        p.fetch(3, 2, 100)
        assertThat((0L..4L).map { p.isCommitted(it) }).containsExactly(true, true, false, false, false)
    }

    @Test
    fun `a stuck follower holds the high watermark back until it leaves the ISR`() {
        val p = partition()
        p.append(10, Acks.ALL)
        p.fetch(2, 10, 1_000) // follower 2 is caught up; follower 3 last caught up at time 0
        assertThat(p.highWatermark()).isEqualTo(0)

        p.shrinkIsr(20_000) // 20 s behind: still inside replica.lag.time.max.ms
        assertThat(p.isr()).containsExactly(1, 2, 3)
        assertThat(p.highWatermark()).isEqualTo(0)

        p.shrinkIsr(30_001) // just past 30 s: out
        assertThat(p.isr()).containsExactly(1, 2)
        assertThat(p.highWatermark()).isEqualTo(10) // the stuck follower no longer counts
    }

    @Test
    fun `fetching is not enough, a follower has to reach the end to stay in the ISR`() {
        val p = partition()
        var t = 0L
        repeat(40) {
            t += 1_000
            p.append(10, Acks.ONE)
            p.fetch(2, p.logEndOffset(1), t)     // keeps up
            p.fetch(3, p.logEndOffset(1) - 5, t) // fetches every second, always 5 records behind
            p.shrinkIsr(t)
        }
        assertThat(p.isr()).containsExactly(1, 2)
    }

    @Test
    fun `the high watermark never moves backwards`() {
        val p = partition()
        p.append(10, Acks.ALL)
        p.fetch(2, 10, 1_000)
        p.shrinkIsr(31_000)
        assertThat(p.highWatermark()).isEqualTo(10)
        p.fetch(3, 0, 32_000) // the old follower comes back, far behind
        assertThat(p.highWatermark()).isEqualTo(10)
        assertThat(p.isr()).containsExactly(1, 2)
    }

    @Test
    fun `a follower rejoins the ISR once it has caught up to the high watermark`() {
        val p = partition()
        p.append(10, Acks.ALL)
        p.fetch(2, 10, 1_000)
        p.shrinkIsr(31_000)
        p.fetch(3, 6, 32_000)
        assertThat(p.isr()).containsExactly(1, 2)
        p.fetch(3, 10, 33_000)
        assertThat(p.isr()).containsExactly(1, 2, 3)
    }

    @Test
    fun `acks=all is refused when the ISR is smaller than min insync replicas, and nothing is written`() {
        val p = partition(minIsr = 2)
        p.append(4, Acks.ALL)
        p.shrinkIsr(31_000) // neither follower ever caught up: the ISR is the leader alone
        assertThat(p.isr()).containsExactly(1)

        assertThatThrownBy { p.append(1, Acks.ALL) }.isInstanceOf(NotEnoughReplicasException::class.java)
        assertThat(p.logEndOffset(1)).isEqualTo(4)
    }

    @Test
    fun `acks=1 ignores min insync replicas`() {
        val p = partition(minIsr = 2)
        p.append(3, Acks.ALL)
        p.shrinkIsr(31_000)
        assertThat(p.isr()).containsExactly(1)
        assertThat(p.append(1, Acks.ONE)).isEqualTo(3)
    }

    @Test
    fun `with the default min insync replicas of 1, the leader alone commits an acks=all write`() {
        val p = partition(minIsr = 1)
        p.append(3, Acks.ALL)
        p.shrinkIsr(31_000)
        val offset = p.append(1, Acks.ALL)
        assertThat(p.isCommitted(offset)).isTrue() // one copy on one disk, and the producer was told "all"
    }

    @Test
    fun `an idle follower that already has everything stays in the ISR`() {
        val p = partition()
        p.append(5, Acks.ALL)
        p.fetch(2, 5, 1_000)
        p.fetch(3, 5, 1_000)
        p.shrinkIsr(120_000) // no new records for two minutes, so nothing to fetch
        assertThat(p.isr()).containsExactly(1, 2, 3)
    }

    @Test
    fun `a fetch past the leader's end is an error`() {
        val p = partition()
        p.append(2, Acks.ALL)
        assertThatThrownBy { p.fetch(2, 3, 0) }.isInstanceOf(IllegalArgumentException::class.java)
    }
}
