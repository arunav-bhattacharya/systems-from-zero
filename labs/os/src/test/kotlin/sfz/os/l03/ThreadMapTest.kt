package sfz.os.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.os.support.Captured

class ThreadMapTest {
    // PaymentWorkers in the lab box: `ps -L -p <pid> -o tid,pcpu,time,comm`, then `jstack <pid>` a moment later
    private val dump = Captured.text("/sfz/os/l03/payment-workers.jstack.txt")
    private val ps = Captured.text("/sfz/os/l03/payment-workers.ps.txt")

    // the header shape JDK 17 and older print: no [tid] and a hex nid
    private val jdk17Dump = """
        "main" #1 prio=5 os_prio=0 cpu=41.47ms elapsed=6.58s tid=0x00007f3c8c016000 nid=0x1b1 waiting on condition  [0x00007f3c93b6c000]
           java.lang.Thread.State: TIMED_WAITING (sleeping)
        	at java.lang.Thread.sleep(java.base@17.0.12/Native Method)
        	at com.example.Settlement.main(Settlement.java:12)

        "Reference Handler" #2 daemon prio=10 os_prio=0 cpu=0.21ms elapsed=6.57s tid=0x00007f3c8c0e1800 nid=0x1b8 waiting on condition  [0x00007f3c6c2f9000]
           java.lang.Thread.State: RUNNABLE
        	at java.lang.ref.Reference.waitForReferencePendingList(java.base@17.0.12/Native Method)
    """.trimIndent()

    @Test
    fun `nidToTid reads decimal (JDK 18 and later) and hex (JDK 17 and older)`() {
        assertThat(ThreadDump.nidToTid("64")).isEqualTo(64)
        assertThat(ThreadDump.nidToTid("0x40")).isEqualTo(64)
        assertThat(ThreadDump.nidToTid("0x1b1")).isEqualTo(433)
    }

    @Test
    fun `parses every thread in a real JDK 25 dump`() {
        val threads = ThreadDump.parse(dump)
        assertThat(threads).hasSize(35)
        assertThat(threads.map { it.name }).contains("main", "fraud-scorer", "ForkJoinPool-1-worker-12", "VM Thread", "GC Thread#0")
        assertThat(threads.map { it.osTid }).doesNotHaveDuplicates()
    }

    @Test
    fun `reads id, TID, daemon flag, state and top frame from a header`() {
        val threads = ThreadDump.parse(dump).associateBy { it.name }
        assertThat(threads["fraud-scorer"]).isEqualTo(DumpedThread(
            name = "fraud-scorer", javaId = 27, osTid = 64, daemon = false, state = "RUNNABLE",
            topFrame = "sfz.os.l03.demo.PaymentWorkers.score(PaymentWorkers.java:45)",
        ))
        assertThat(threads["ledger-writer-1"]!!.state).isEqualTo("TIMED_WAITING")
        assertThat(threads["Reference Handler"]!!.daemon).isTrue()
    }

    @Test
    fun `JVM-internal threads have a TID but no Java id, state or stack`() {
        val vmThread = ThreadDump.parse(dump).single { it.name == "VM Thread" }
        assertThat(vmThread).isEqualTo(DumpedThread("VM Thread", null, 52, false, null, null))
    }

    @Test
    fun `parses a JDK 17 style dump with hex nids`() {
        val threads = ThreadDump.parse(jdk17Dump)
        assertThat(threads.map { it.name to it.osTid }).containsExactly("main" to 433, "Reference Handler" to 440)
        assertThat(threads[0].topFrame).isEqualTo("java.lang.Thread.sleep(java.base@17.0.12/Native Method)")
        assertThat(threads[1].daemon).isTrue()
    }

    @Test
    fun `the hottest kernel task is the fraud-scorer thread`() {
        val (task, thread) = ThreadMap(ThreadDump.parse(dump), PsThreads.parse(ps)).hottest()
        assertThat(task.tid).isEqualTo(64)
        assertThat(task.cpuPercent).isGreaterThan(90.0)
        assertThat(thread!!.name).isEqualTo("fraud-scorer")
        assertThat(thread.topFrame).startsWith("sfz.os.l03.demo.PaymentWorkers.score")
    }

    @Test
    fun `joins on the TID because the kernel cuts names to 15 characters`() {
        val map = ThreadMap(ThreadDump.parse(dump), PsThreads.parse(ps))
        val task = PsThreads.parse(ps).single { it.tid == 77 }
        assertThat(task.comm).isEqualTo("ForkJoinPool-1-")
        assertThat(map.javaThreadFor(77)!!.name).isEqualTo("ForkJoinPool-1-worker-11")
        assertThat(map.javaThreadFor(999_999)).isNull()
    }

    @Test
    fun `finds the one task jstack does not list, the launcher thread whose TID is the PID`() {
        val notInDump = ThreadMap(ThreadDump.parse(dump), PsThreads.parse(ps)).tasksNotInDump()
        assertThat(notInDump).containsExactly(OsTask(40, 0.0, "java"))
    }
}
