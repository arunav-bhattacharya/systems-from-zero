package sfz.os.l12

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.os.support.Captured

class ContainersTest {
    private val byHand = Captured.lines("/sfz/os/l12/cgroup-by-hand.txt")
    private val container = Captured.lines("/sfz/os/l12/container-by-hand.txt")
    private val nspid = Captured.lines("/sfz/os/l12/nspid.txt")
    private val jvm = Captured.text("/sfz/os/l12/jvm-limits.txt")

    private fun number(lines: List<String>, re: String): Int = lines.firstNotNullOf { Regex(re).find(it)?.groupValues?.get(1)?.toInt() }

    /** The box-priv set-up: a cgroup "ledger" with pids.max 20 and memory.max 64M, and a shell in it. */
    private fun ledger(h: Host): Pair<Cgroup, Task> {
        val cg = h.mkdir("ledger")
        cg.pidsMax = 20
        cg.memoryMaxMb = 64
        val shell = h.boot("bash")
        h.move(shell, cg)
        return cg to shell
    }

    @Test
    fun `fork past pids_max fails with EAGAIN and pids_events counts it`() {
        val h = Host()
        val (cg, shell) = ledger(h)
        val forks = shell                                                   // bash -c execs its last command: forks.c is bash's task

        var children = 0
        val error = runCatching { while (true) { h.fork(forks, "child"); children++ } }.exceptionOrNull()
        assertThat(error).isInstanceOf(SysError::class.java).hasMessageContaining("EAGAIN")
        assertThat(children).isEqualTo(number(byHand, """^(\d+) children running"""))    // 19 children + forks.c = 20 tasks
        assertThat(children + 1).isEqualTo(number(byHand, """fork number (\d+) failed"""))
        assertThat(cg.pidsEventsMax).isEqualTo(number(byHand, """^max (\d+)$"""))        // pids.events: max 1
        assertThat(cg.pidsCurrent).isEqualTo(20)
    }

    @Test
    fun `threads count against pids_max too`() {
        val h = Host()
        val (cg, shell) = ledger(h)
        val jvm = h.fork(shell, "java")
        repeat(18) { h.startThread(jvm, "worker-$it") }
        assertThatThrownBy { h.startThread(jvm, "one-too-many") }.hasMessageContaining("EAGAIN")
        assertThat(cg.pidsEventsMax).isEqualTo(1)
    }

    @Test
    fun `a parent cgroup's pids_max limits every cgroup below it`() {
        val h = Host()
        val pod = h.mkdir("pod")
        pod.pidsMax = 3
        val app = h.mkdir("app", pod)                                       // no limit of its own
        val shell = h.boot("sh")
        h.move(shell, app)
        h.fork(shell)
        h.fork(shell)
        assertThatThrownBy { h.fork(shell) }.hasMessageContaining("EAGAIN")
        assertThat(pod.pidsEventsMax).isEqualTo(1)                          // the cgroup whose limit was hit
        assertThat(app.pidsEventsMax).isZero()
    }

    @Test
    fun `memory_max calls the OOM killer inside the cgroup, and hog_c dies on its 64 MB step`() {
        val h = Host()
        val (cg, shell) = ledger(h)
        shell.rssMb = 4                                                     // bash itself
        val hog = h.fork(shell, "hog")
        val held = mutableListOf<Int>()
        for (mb in 16..256 step 16) {
            val killed = h.touch(hog, 16)
            if (!hog.alive) break
            assertThat(killed).isEmpty()
            held += mb
        }
        val lastLine = byHand.last { it.startsWith("holding") }
        assertThat("holding ${held.last()} MB").isEqualTo(lastLine)        // holding 48 MB, then SIGKILL
        assertThat(hog.killedBy).contains("OOM")
        assertThat(shell.alive).isTrue()                                    // the small task survives
        assertThat(cg.memoryEventsOom).isEqualTo(number(byHand, """^oom (\d+)$"""))
        assertThat(cg.memoryEventsOomKill).isEqualTo(number(byHand, """^oom_kill (\d+)$"""))
        assertThat(cg.memoryEventsMax).isPositive()
        assertThat(cg.memoryCurrentMb).isLessThanOrEqualTo(64)
    }

    @Test
    fun `the OOM killer picks the biggest task in the cgroup, not the one that asked last`() {
        val h = Host()
        val pod = h.mkdir("pod")
        pod.memoryMaxMb = 1536
        val java = h.boot("java")
        val script = h.boot("report.sh")
        h.move(java, pod)
        h.move(script, pod)
        h.touch(java, 1200)
        h.touch(script, 50)
        val outside = h.boot("kafka")                                       // not in the cgroup, and bigger than both
        h.touch(outside, 4000)

        val killed = h.touch(script, 300)                                   // the script's allocation crosses the limit
        assertThat(killed).containsExactly(java)
        assertThat(script.alive).isTrue()
        assertThat(outside.alive).isTrue()
        assertThat(pod.memoryEventsOomKill).isEqualTo(1)
    }

    @Test
    fun `the first task in a new PID namespace is PID 1 inside and keeps its host PID outside`() {
        val h = Host()
        repeat(39) { h.boot("other") }                                      // the host has been busy: PIDs 2 to 40
        val unshare = h.boot("unshare")
        val shell = h.forkIntoNewPidNamespace(unshare, "bash")
        val ps = h.fork(shell, "ps")

        assertThat(shell.pid).isEqualTo(1)
        assertThat(shell.hostPid).isEqualTo(42)
        assertThat(shell.nsPidLine).isEqualTo("NSpid:\t42\t1")
        assertThat(ps.pids).containsExactly(43, 2)
        assertThat(unshare.nsPidLine).isEqualTo("NSpid:\t41")               // still in the host namespace
        assertThat(h.find(shell.ns, 1)).isSameAs(shell)
        assertThat(h.find(h.hostNs, 42)).isSameAs(shell)
        // the lab box showed the same shape: one level for the host's own tasks, two inside
        assertThat(nspid.first { it.startsWith("NSpid") }.split('\t')).hasSize(3).last().isEqualTo("1")
        assertThat(container.filter { it.contains("NSpid") }.map { it.substringAfter("NSpid:").trim().split('\t').size }).containsExactly(1, 2, 2)
    }

    @Test
    fun `when PID 1 of a namespace dies, every task in it dies too`() {
        val h = Host()
        val unshare = h.boot("unshare")
        val init = h.forkIntoNewPidNamespace(unshare, "java")
        val helper = h.fork(init, "pdftotext")
        h.kill(init)
        assertThat(helper.alive).isFalse()
        assertThat(unshare.alive).isTrue()
    }

    @Test
    fun `the JVM rounds the CPU quota up and is capped by the CPUs it may use`() {
        assertThat(JvmView.availableProcessors("150000 100000", 12)).isEqualTo(Regex("""Effective CPU Count: (\d+)""").find(jvm)!!.groupValues[1].toInt())
        assertThat(JvmView.availableProcessors("400000 100000", 12)).isEqualTo(4)
        assertThat(JvmView.availableProcessors("50000 100000", 12)).isEqualTo(1)
        assertThat(JvmView.availableProcessors("max 100000", 12)).isEqualTo(12)
        assertThat(JvmView.availableProcessors("800000 100000", 2)).isEqualTo(2)    // --cpus 8 with --cpuset-cpus 0,1
    }

    @Test
    fun `the JVM picks Serial below 2 CPUs or 1792 MB, and G1 above`() {
        val serial1g = jvm.substringAfter("== --memory 1g --cpus 1.5\n").substringBefore("==")
        val g1at4g = jvm.substringAfter("== --memory 4g --cpus 4\n").substringBefore("==")
        assertThat(serial1g).containsPattern("UseSerialGC +=  *true")
        assertThat(g1at4g).containsPattern("UseG1GC +=  *true")

        assertThat(JvmView.defaultGc(cpus = 2, memoryMb = 1024)).isEqualTo("Serial")   // the 1g, 1.5 CPU container
        assertThat(JvmView.defaultGc(cpus = 4, memoryMb = 4096)).isEqualTo("G1")
        assertThat(JvmView.defaultGc(cpus = 1, memoryMb = 8192)).isEqualTo("Serial")
        assertThat(JvmView.defaultGc(cpus = 2, memoryMb = 1792)).isEqualTo("G1")
    }
}
