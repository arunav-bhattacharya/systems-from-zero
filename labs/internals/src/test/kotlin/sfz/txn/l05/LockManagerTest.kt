package sfz.txn.l05

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.txn.l05.LockMode.EXCLUSIVE
import sfz.txn.l05.LockMode.SHARED

class LockManagerTest {
    private val locks = LockManager()

    @Test
    fun `shared locks are compatible`() {
        assertThat(locks.acquire(1, "acct-1", SHARED)).isTrue()
        assertThat(locks.acquire(2, "acct-1", SHARED)).isTrue()
        assertThat(locks.holders("acct-1")).isEqualTo(mapOf(1L to SHARED, 2L to SHARED))
    }

    @Test
    fun `an exclusive lock conflicts with every other lock`() {
        assertThat(locks.acquire(1, "acct-1", SHARED)).isTrue()
        assertThat(locks.acquire(2, "acct-1", EXCLUSIVE)).`as`("X after S").isFalse()
        assertThat(locks.acquire(3, "acct-2", EXCLUSIVE)).isTrue()
        assertThat(locks.acquire(4, "acct-2", SHARED)).`as`("S after X").isFalse()
        assertThat(locks.acquire(5, "acct-3", EXCLUSIVE)).isTrue()
        assertThat(locks.acquire(6, "acct-3", EXCLUSIVE)).`as`("X after X").isFalse()
        assertThat(locks.waitingFor(2)).isEqualTo("acct-1")
        assertThat(locks.waiters("acct-2")).containsExactly(4L)
        assertThat(locks.holders("acct-3")).isEqualTo(mapOf(5L to EXCLUSIVE))
        assertThatThrownBy { locks.acquire(2, "acct-9", SHARED) }.`as`("a waiting transaction can't ask for more")
            .isInstanceOf(IllegalStateException::class.java)
    }

    @Test
    fun `asking again for a lock you hold is granted at once`() {
        assertThat(locks.acquire(1, "acct-1", EXCLUSIVE)).isTrue()
        assertThat(locks.acquire(1, "acct-1", SHARED)).`as`("S while holding X").isTrue()
        assertThat(locks.acquire(1, "acct-1", EXCLUSIVE)).`as`("X again").isTrue()
        assertThat(locks.acquire(2, "acct-2", SHARED)).isTrue()
        assertThat(locks.acquire(2, "acct-2", SHARED)).`as`("S again").isTrue()
        assertThat(locks.holders("acct-1")).isEqualTo(mapOf(1L to EXCLUSIVE))
        assertThat(locks.holders("acct-2")).isEqualTo(mapOf(2L to SHARED))
    }

    @Test
    fun `release grants the waiting requests in arrival order`() {
        locks.acquire(1, "acct-1", EXCLUSIVE)
        locks.acquire(2, "acct-1", SHARED)
        locks.acquire(3, "acct-1", SHARED)
        locks.acquire(4, "acct-1", EXCLUSIVE)
        locks.acquire(5, "acct-1", SHARED)
        assertThat(locks.release(1)).`as`("woken when T1 releases").containsExactly(2L, 3L)
        assertThat(locks.holders("acct-1")).isEqualTo(mapOf(2L to SHARED, 3L to SHARED))
        assertThat(locks.waiters("acct-1")).`as`("T5 stays behind T4").containsExactly(4L, 5L)
        assertThat(locks.release(2)).isEmpty()
        assertThat(locks.release(3)).containsExactly(4L)
        assertThat(locks.release(4)).containsExactly(5L)
        assertThat(locks.release(5)).isEmpty()
        assertThat(locks.holders("acct-1")).isEmpty()
    }

    @Test
    fun `release frees every lock the transaction holds`() {
        locks.acquire(1, "acct-1", EXCLUSIVE)
        locks.acquire(1, "acct-2", EXCLUSIVE)
        locks.acquire(1, "acct-3", SHARED)
        locks.acquire(2, "acct-2", SHARED)
        locks.acquire(3, "acct-3", SHARED)
        assertThat(locks.release(1)).containsExactly(2L)
        assertThat(locks.holders("acct-1")).isEmpty()
        assertThat(locks.holders("acct-2")).isEqualTo(mapOf(2L to SHARED))
        assertThat(locks.holders("acct-3")).isEqualTo(mapOf(3L to SHARED))
    }

    @Test
    fun `a shared request does not jump ahead of a waiting exclusive request`() {
        // a long report holds S; a migration asks for X and waits; now a plain read arrives
        assertThat(locks.acquire(1, "accounts", SHARED)).isTrue()
        assertThat(locks.acquire(2, "accounts", EXCLUSIVE)).isFalse()
        assertThat(locks.acquire(3, "accounts", SHARED)).`as`("compatible with T1, but T2 is ahead").isFalse()
        assertThat(locks.waiters("accounts")).containsExactly(2L, 3L)
        assertThat(locks.release(1)).containsExactly(2L)
        assertThat(locks.release(2)).containsExactly(3L)
    }

    @Test
    fun `the only holder upgrades at once, a second holder makes the upgrade wait`() {
        locks.acquire(1, "acct-1", SHARED)
        assertThat(locks.acquire(1, "acct-1", EXCLUSIVE)).`as`("sole holder").isTrue()
        assertThat(locks.holders("acct-1")).isEqualTo(mapOf(1L to EXCLUSIVE))

        locks.acquire(2, "acct-2", SHARED)
        locks.acquire(3, "acct-2", SHARED)
        locks.acquire(4, "acct-2", EXCLUSIVE)                     // waits
        assertThat(locks.acquire(2, "acct-2", EXCLUSIVE)).`as`("T3 also holds S").isFalse()
        assertThat(locks.waiters("acct-2")).`as`("the upgrade waits ahead of T4").containsExactly(2L, 4L)
        assertThat(locks.release(3)).containsExactly(2L)
        assertThat(locks.holders("acct-2")).isEqualTo(mapOf(2L to EXCLUSIVE))
        assertThat(locks.waiters("acct-2")).containsExactly(4L)
    }

    @Test
    fun `release also cancels a waiting request`() {
        locks.acquire(1, "acct-1", EXCLUSIVE)
        locks.acquire(2, "acct-1", EXCLUSIVE)
        locks.acquire(3, "acct-1", SHARED)
        assertThat(locks.release(2)).`as`("T2 gives up while waiting").isEmpty()
        assertThat(locks.waitingFor(2)).isNull()
        assertThat(locks.waiters("acct-1")).containsExactly(3L)
        assertThat(locks.release(1)).containsExactly(3L)
    }

    @Test
    fun `the waits-for graph points from each waiter to the conflicting requests ahead of it`() {
        locks.acquire(1, "acct-1", SHARED)
        locks.acquire(2, "acct-1", SHARED)
        locks.acquire(3, "acct-1", EXCLUSIVE)                     // waits for T1 and T2
        locks.acquire(4, "acct-1", SHARED)                        // waits behind T3 only
        locks.acquire(5, "acct-2", EXCLUSIVE)
        locks.acquire(6, "acct-2", SHARED)                        // waits for T5
        assertThat(locks.waitsFor()).isEqualTo(
            mapOf(3L to setOf(1L, 2L), 4L to setOf(3L), 6L to setOf(5L)),
        )
    }

    @Test
    fun `a chain of waits is not a deadlock`() {
        locks.acquire(1, "acct-1", EXCLUSIVE)
        locks.acquire(2, "acct-2", EXCLUSIVE)
        locks.acquire(3, "acct-3", EXCLUSIVE)
        locks.acquire(2, "acct-1", EXCLUSIVE)                     // T2 waits for T1
        locks.acquire(3, "acct-2", EXCLUSIVE)                     // T3 waits for T2
        assertThat(locks.findCycle()).isNull()
        assertThat(locks.detectDeadlocks()).isEmpty()
        assertThat(locks.wasAborted(3)).isFalse()
    }

    @Test
    fun `two transfers in opposite order deadlock, and the youngest is aborted`() {
        // T1 moves money from acct-1 to acct-2, T2 from acct-2 to acct-1
        assertThat(locks.acquire(1, "acct-1", EXCLUSIVE)).isTrue()
        assertThat(locks.acquire(2, "acct-2", EXCLUSIVE)).isTrue()
        assertThat(locks.acquire(1, "acct-2", EXCLUSIVE)).isFalse()
        assertThat(locks.acquire(2, "acct-1", EXCLUSIVE)).isFalse()
        assertThat(locks.findCycle()).containsExactly(1L, 2L)
        assertThat(locks.detectDeadlocks()).containsExactly(2L)
        assertThat(locks.wasAborted(2)).isTrue()
        assertThat(locks.holders("acct-2")).`as`("T1 got acct-2 when T2 was aborted").isEqualTo(mapOf(1L to EXCLUSIVE))
        assertThat(locks.waitingFor(1)).isNull()
        assertThat(locks.findCycle()).isNull()
    }

    @Test
    fun `a cycle of three is found, and only a transaction on it is aborted`() {
        locks.acquire(1, "acct-1", EXCLUSIVE)
        locks.acquire(2, "acct-2", EXCLUSIVE)
        locks.acquire(3, "acct-3", EXCLUSIVE)
        locks.acquire(9, "acct-9", EXCLUSIVE)
        locks.acquire(1, "acct-2", EXCLUSIVE)                     // T1 -> T2
        locks.acquire(2, "acct-3", EXCLUSIVE)                     // T2 -> T3
        locks.acquire(3, "acct-1", SHARED)                        // T3 -> T1: the cycle closes
        locks.acquire(4, "acct-9", SHARED)                        // T4 -> T9: a chain off to the side
        locks.acquire(9, "acct-1", SHARED)                        // T9 -> T1: waits on the cycle, isn't on it
        assertThat(locks.findCycle()).containsExactly(1L, 2L, 3L)
        assertThat(locks.detectDeadlocks()).`as`("the youngest on the cycle, not T9").containsExactly(3L)
        assertThat(locks.holders("acct-3")).isEqualTo(mapOf(2L to EXCLUSIVE))
        assertThat(locks.wasAborted(9)).isFalse()
        assertThat(locks.waitingFor(9)).`as`("T9 still waits for T1, which is fine").isEqualTo("acct-1")
    }

    @Test
    fun `two readers that both upgrade to write deadlock`() {
        // both run SELECT ... then UPDATE on the same row
        locks.acquire(1, "acct-1", SHARED)
        locks.acquire(2, "acct-1", SHARED)
        assertThat(locks.acquire(1, "acct-1", EXCLUSIVE)).isFalse()
        assertThat(locks.acquire(2, "acct-1", EXCLUSIVE)).isFalse()
        assertThat(locks.findCycle()).containsExactly(1L, 2L)
        assertThat(locks.detectDeadlocks()).containsExactly(2L)
        assertThat(locks.holders("acct-1")).isEqualTo(mapOf(1L to EXCLUSIVE))
    }

    @Test
    fun `a request queued behind another waiter can close a cycle`() {
        locks.acquire(3, "acct-3", EXCLUSIVE)
        locks.acquire(1, "acct-1", SHARED)
        locks.acquire(2, "acct-1", EXCLUSIVE)                     // T2 waits for T1
        locks.acquire(3, "acct-1", SHARED)                        // T3 waits behind T2, though T1 only holds S
        locks.acquire(1, "acct-3", SHARED)                        // T1 waits for T3
        assertThat(locks.waitsFor()[3L]).`as`("T3's edge goes to the waiter ahead of it").containsExactly(2L)
        assertThat(locks.findCycle()).containsExactly(1L, 3L, 2L)
        assertThat(locks.detectDeadlocks()).containsExactly(3L)
        assertThat(locks.holders("acct-3")).isEqualTo(mapOf(1L to SHARED))
        assertThat(locks.waiters("acct-1")).`as`("T3's waiting request went with it").containsExactly(2L)
    }
}
