package sfz.os.l07

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test
import sfz.os.support.Captured

class CopyOnWriteTest {
    // cow.c in the lab box: touch 512 MB, fork, then the child writes one byte in every 4th page
    private val run = Captured.lines("/sfz/os/l07/cow-512m.txt")

    /** The Pss, Shared and Private numbers (MB) of one line of the captured run. */
    private fun captured(who: String): List<Long> {
        val line = run.first { it.startsWith(who) }
        return listOf("Pss", "Shared", "Private").map { Regex("""$it +(\d+) MB""").find(line)!!.groupValues[1].toLong() }
    }

    private val mbPages = 256                       // 1 MB of 4 KB pages
    private val pages512 = 512L * mbPages           // 131,072

    /** A process that has written every page of a 512 MB region, like cow.c before it forks. */
    private fun bigParent(k: Kernel): Pair<Process, LongRange> {
        val parent = k.spawn("cow")
        val region = k.mmap(parent, pages512)
        for (vpn in region) k.write(parent, vpn)
        return parent to region
    }

    private fun Smaps.mb(): List<Long> = listOf((pss / mbPages).toLong(), shared.toLong() / mbPages, private.toLong() / mbPages)

    @Test
    fun `fork shares every page and copies none`() {
        val k = Kernel(limitFrames = 1 shl 20)
        val (parent, _) = bigParent(k)
        val child = k.fork(parent)

        assertThat(k.copies).isZero()
        assertThat(k.ram.used).isEqualTo(pages512.toInt())        // still one frame per page
        assertThat(k.smaps(child)).isEqualTo(Smaps(rss = 131_072, shared = 131_072, private = 0, pss = 65_536.0))
        assertThat(k.smaps(child).mb()).isEqualTo(captured("child after fork"))   // Pss 256, Shared 512, Private 0
    }

    @Test
    fun `the first write after fork copies the page and the second write to it copies nothing`() {
        val k = Kernel(limitFrames = 100)
        val parent = k.spawn("ledger")
        val region = k.mmap(parent, 10)
        for (vpn in region) k.write(parent, vpn)
        val child = k.fork(parent, "child")

        assertThat(k.write(child, region.first)).isEqualTo(Fault.COPY)
        assertThat(k.write(child, region.first)).isEqualTo(Fault.NONE)   // the copy is the child's own, writable
        assertThat(k.copies).isEqualTo(1L)
        assertThat(k.ram.used).isEqualTo(11)
        assertThat(k.smaps(parent)).isEqualTo(Smaps(rss = 10, shared = 9, private = 1, pss = 5.5))
    }

    @Test
    fun `reads after fork copy nothing, and the parent's writes copy too`() {
        val k = Kernel(limitFrames = 100)
        val parent = k.spawn("ledger")
        val region = k.mmap(parent, 4)
        for (vpn in region) k.write(parent, vpn)
        val child = k.fork(parent, "child")

        for (vpn in region) k.read(child, vpn)
        assertThat(k.copies).isZero()
        assertThat(k.write(parent, region.last)).isEqualTo(Fault.COPY)   // fork made the parent's entries read-only too
        assertThat(k.smaps(child).private).isEqualTo(1)                  // the child is now the only user of the old frame
    }

    @Test
    fun `replaying cow_c gives the same Shared, Private and Pss as smaps_rollup`() {
        val k = Kernel(limitFrames = 1 shl 20)
        val (parent, region) = bigParent(k)
        val child = k.fork(parent)
        for (vpn in region step 4) k.write(child, vpn)

        val faults = Regex("""(\d+) page faults""").find(run.first { it.startsWith("child wrote") })!!.groupValues[1].toLong()
        assertThat(k.copies).isEqualTo(faults)                            // 32,768: one copy per page written
        assertThat(k.smaps(child).mb()).isEqualTo(captured("child after writes"))   // Pss 320, Shared 384, Private 128
        assertThat(k.ram.used).isEqualTo(131_072 + 32_768)                // 640 MB for two processes that each "use" 512
    }

    @Test
    fun `after the child exits, the parent's writes reuse its frames without copying`() {
        val k = Kernel(limitFrames = 100)
        val parent = k.spawn("api")
        val region = k.mmap(parent, 8)
        for (vpn in region) k.write(parent, vpn)
        val child = k.fork(parent, "child")
        k.exit(child)

        assertThat(region.map { k.write(parent, it) }).containsOnly(Fault.REUSE)
        assertThat(k.copies).isZero()
        assertThat(k.smaps(parent)).isEqualTo(Smaps(rss = 8, shared = 0, private = 8, pss = 8.0))
        assertThat(k.write(parent, region.first)).isEqualTo(Fault.NONE)
    }

    @Test
    fun `PSS splits each shared page among every process that maps it`() {
        val k = Kernel(limitFrames = 1000)
        val parent = k.spawn("worker-pool")
        val region = k.mmap(parent, 300)
        for (vpn in region) k.write(parent, vpn)
        val a = k.fork(parent, "a")
        val b = k.fork(parent, "b")

        for (p in listOf(parent, a, b)) assertThat(k.smaps(p).pss).isCloseTo(100.0, within(1e-9))
        assertThat(k.processes.sumOf { k.smaps(it).pss }).isCloseTo(k.ram.used.toDouble(), within(1e-9))
        assertThat(k.processes.sumOf { it.rss }).isEqualTo(900)          // RSS counts every shared page three times
    }

    @Test
    fun `when the limit is reached the kernel kills the biggest process, not the one that asked`() {
        val k = Kernel(limitFrames = 1000)
        val cache = k.spawn("cache")
        for (vpn in k.mmap(cache, 700)) k.write(cache, vpn)
        val worker = k.spawn("worker")
        val heap = k.mmap(worker, 350)
        val faults = heap.map { k.write(worker, it) }

        assertThat(faults).containsOnly(Fault.ZERO_FILL)                 // the worker never noticed
        assertThat(k.oomKills).containsExactly(cache.pid)
        assertThat(cache.alive).isFalse()
        assertThat(k.ram.used).isEqualTo(350)
    }

    @Test
    fun `oom_score_adj -1000 protects a process, so the one asking dies instead`() {
        val k = Kernel(limitFrames = 1000)
        val db = k.spawn("database").apply { oomScoreAdj = -1000 }
        for (vpn in k.mmap(db, 900)) k.write(db, vpn)
        val batch = k.spawn("batch")
        val heap = k.mmap(batch, 200).toList()
        val faults = heap.map { if (batch.alive) k.write(batch, it) else null }.filterNotNull()

        assertThat(faults.last()).isEqualTo(Fault.KILLED)
        assertThat(faults.count { it == Fault.ZERO_FILL }).isEqualTo(100)
        assertThat(k.oomKills).containsExactly(batch.pid)
        assertThat(db.alive).isTrue()
    }

    @Test
    fun `a forked child that rewrites everything doubles the memory and gets OOM-killed`() {
        // Redis-style snapshot: the parent holds 600 pages, forks, and the child touches every page
        val k = Kernel(limitFrames = 1000)
        val server = k.spawn("server")
        val data = k.mmap(server, 600)
        for (vpn in data) k.write(server, vpn)
        val snapshot = k.fork(server, "snapshot")
        val faults = data.map { if (snapshot.alive) k.write(snapshot, it) else null }.filterNotNull()

        assertThat(faults.count { it == Fault.COPY }).isEqualTo(400)    // 600 + 400 = the 1000-frame limit
        assertThat(faults.last()).isEqualTo(Fault.KILLED)               // equal RSS, so the newer process dies
        assertThat(k.oomKills).containsExactly(snapshot.pid)
        assertThat(server.alive).isTrue()
        assertThat(k.ram.used).isEqualTo(600)                           // the copies are freed with the child
        assertThat(k.smaps(server).private).isEqualTo(600)
    }
}
