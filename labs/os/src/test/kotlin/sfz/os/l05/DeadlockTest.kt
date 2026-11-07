package sfz.os.l05

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.os.support.Captured

class DeadlockTest {
    // jstack -l of this lesson's Transfers demo (synchronized), and of the same deadlock built with ReentrantLock
    private val monitors = Captured.text("/sfz/os/l05/transfers-deadlock.jstack.txt")
    private val reentrant = Captured.text("/sfz/os/l05/lock-transfers-deadlock.jstack.txt")

    @Test
    fun `reads what each thread holds and waits for in a synchronized deadlock`() {
        val threads = LockDump.parse(monitors).associateBy { it.thread }
        assertThat(threads["refund"]).isEqualTo(ThreadLocks("refund", listOf("0x000000008bb18d30"), "0x000000008bb18d78"))
        assertThat(threads["payment"]).isEqualTo(ThreadLocks("payment", listOf("0x000000008bb18d78"), "0x000000008bb18d30"))
    }

    @Test
    fun `a thread in Object wait holds nothing it waits for, and the summary at the end is not a thread`() {
        val threads = LockDump.parse(monitors)
        assertThat(threads.map { it.thread }).doesNotHaveDuplicates().contains("main", "VM Thread", "GC Thread#0")
        assertThat(threads).hasSize(20)
        // main is in Thread.join, which is Object.wait: "- waiting on" is not a lock wait
        assertThat(threads.single { it.thread == "main" }.waitingFor).isNull()
        assertThat(threads.filter { it.waitingFor != null }.map { it.thread }).containsExactly("refund", "payment")
    }

    @Test
    fun `reads ReentrantLock holders from Locked ownable synchronizers`() {
        val threads = LockDump.parse(reentrant).associateBy { it.thread }
        assertThat(threads["refund"]).isEqualTo(ThreadLocks("refund", listOf("0x000000008bb16ff0"), "0x000000008bb17020"))
        assertThat(threads["payment"]).isEqualTo(ThreadLocks("payment", listOf("0x000000008bb17020"), "0x000000008bb16ff0"))
        assertThat(threads.values.filter { it.waitingFor != null }.map { it.thread }).containsExactly("refund", "payment")
    }

    @Test
    fun `the wait-for graph of the real dump is one cycle of two threads`() {
        for (dump in listOf(monitors, reentrant)) {
            val graph = WaitForGraph(LockDump.parse(dump))
            assertThat(graph.edges()).isEqualTo(mapOf("refund" to "payment", "payment" to "refund"))
            assertThat(graph.findCycle()).containsExactly("payment", "refund")
        }
    }

    @Test
    fun `a chain of waits that ends at a running thread is not a deadlock`() {
        val graph = WaitForGraph(listOf(
            ThreadLocks("settlement", listOf("0xa"), "0xb"),
            ThreadLocks("ledger-writer", listOf("0xb"), "0xc"),
            ThreadLocks("audit", listOf("0xc"), null),            // holds 0xc and is still running
            ThreadLocks("reporter", emptyList(), "0xd"),         // waits for a lock nobody holds: no edge
        ))
        assertThat(graph.edges()).isEqualTo(mapOf("settlement" to "ledger-writer", "ledger-writer" to "audit"))
        assertThat(graph.findCycle()).isNull()
    }

    @Test
    fun `finds a three-thread cycle and starts it at the first name`() {
        val graph = WaitForGraph(listOf(
            ThreadLocks("t3", listOf("C"), "A"),
            ThreadLocks("t1", listOf("A"), "B"),
            ThreadLocks("t2", listOf("B"), "C"),
            ThreadLocks("bystander", emptyList(), "A"),          // waits on the cycle but is not part of it
        ))
        assertThat(graph.findCycle()).containsExactly("t1", "t2", "t3")
    }

    @Test
    fun `each fix breaks one Coffman condition`() {
        assertThat(Fix.LOCK_ORDERING.breaks()).isEqualTo(Coffman.CIRCULAR_WAIT)
        assertThat(Fix.ALL_LOCKS_AT_ONCE.breaks()).isEqualTo(Coffman.HOLD_AND_WAIT)
        assertThat(Fix.TRY_LOCK_AND_BACK_OFF.breaks()).isEqualTo(Coffman.NO_PREEMPTION)
        assertThat(Fix.LOCK_FREE.breaks()).isEqualTo(Coffman.MUTUAL_EXCLUSION)
        assertThat(Fix.entries.map { it.breaks() }).doesNotHaveDuplicates()
    }

    @Test
    fun `the naive transfers deadlock in 2 of their 6 schedules, the ordered ones never`() {
        val naive = Schedules.explore(mapOf(
            "refund" to Schedules.transfer("ACC-1001", "ACC-2002"),
            "payment" to Schedules.transfer("ACC-2002", "ACC-1001"),
        ))
        assertThat(naive.finished to naive.deadlocked).isEqualTo(4 to 2)
        assertThat(naive.firstDeadlock).containsExactly("refund locks ACC-1001", "payment locks ACC-2002")

        assertThat(Schedules.orderedTransfer("ACC-2002", "ACC-1001").first()).isEqualTo(Op.Lock("ACC-1001"))
        val ordered = Schedules.explore(mapOf(
            "refund" to Schedules.orderedTransfer("ACC-1001", "ACC-2002"),
            "payment" to Schedules.orderedTransfer("ACC-2002", "ACC-1001"),
        ))
        assertThat(ordered.deadlocked).isZero()
        assertThat(ordered.finished).isEqualTo(2)
    }

    @Test
    fun `lock ordering also fixes a ring of three transfers`() {
        fun ring(transfer: (String, String) -> List<Op>) = Schedules.explore(mapOf(
            "t1" to transfer("A", "B"), "t2" to transfer("B", "C"), "t3" to transfer("C", "A"),
        ))
        assertThat(ring(Schedules::transfer).deadlocked).isEqualTo(6)
        assertThat(ring(Schedules::orderedTransfer).deadlocked).isZero()
    }
}
