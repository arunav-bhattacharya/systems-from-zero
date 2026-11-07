package sfz.os.l08

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.os.support.Captured

class MallocTest {
    private val mb = 1L shl 20

    /** The strace of sizes.c, turned into the model's log format: "brk +N", "mmap N", "munmap N". */
    private fun capturedSyscalls(): List<String> {
        var brk = -1L
        val out = mutableListOf<String>()
        for (line in Captured.lines("/sfz/os/l08/sizes.strace.txt")) {
            Regex("""^brk\((\w+)\)\s+= 0x([0-9a-f]+)""").find(line)?.let { m ->
                val now = m.groupValues[2].toLong(16)
                if (m.groupValues[1] != "NULL") out += "brk +${now - brk}"
                brk = now
            }
            Regex("""^mmap\(NULL, (\d+),""").find(line)?.let { out += "mmap ${it.groupValues[1]}" }
            Regex("""^munmap\(0x[0-9a-f]+, (\d+)\)""").find(line)?.let { out += "munmap ${it.groupValues[1]}" }
        }
        return out
    }

    /** "label: RSS n MB, heap m MB" lines of one frag.c run (the file holds two runs of five lines). */
    private fun fragRun(index: Int): List<Pair<Long, Long>> =
        Captured.lines("/sfz/os/l08/frag.txt").filter { "RSS" in it }.drop(5 * index).take(5).map { line ->
            val (rss, heap) = Regex("""RSS +(\d+) MB, heap +(\d+) MB""").find(line)!!.destructured
            rss.toLong() to heap.toLong()
        }

    @Test
    fun `replaying sizes_c makes the same system calls as glibc`() {
        val heap = Heap()
        heap.malloc(1000)                                   // brk +132 KB: the chunk plus 128 KB of top pad
        heap.malloc(1000)                                   // from the top chunk: no system call
        heap.malloc(100 * 1024)                             // still fits in the top chunk
        heap.malloc(200 * 1024)                             // over the 128 KB threshold and too big for the top: mmap
        val big = heap.malloc(1 * mb)
        heap.free(big)                                      // munmap, and the threshold rises to the block's size
        heap.malloc(1 * mb)                                 // now under the threshold: the heap grows with brk instead

        assertThat(heap.syscalls).containsExactlyElementsOf(capturedSyscalls())
        assertThat(heap.mmapThreshold).isEqualTo(1_052_672L)
        // glibc's chunk sizes: n + 8 bytes, rounded up to 16, at least 32 (1000 -> 1008, 200 KB -> 204,816)
        assertThat(listOf(1L, 24L, 25L, 1000L, 204_800L).map(Sizes::chunkSize)).containsExactly(32L, 32L, 48L, 1008L, 204_816L)
    }

    @Test
    fun `neighbouring free chunks merge back into one`() {
        val heap = Heap()
        val a = heap.malloc(1000)
        val b = heap.malloc(1000)
        val c = heap.malloc(1000)
        heap.malloc(1000)                                   // keeps the three away from the top chunk
        heap.free(a)
        heap.free(c)
        val elsewhere = heap.malloc(3000)                   // two 1,008-byte holes: neither fits 3,008 bytes
        assertThat(elsewhere).isNotEqualTo(a)
        heap.free(elsewhere)
        heap.free(b)                                        // b joins a on its left and c on its right
        assertThat(heap.malloc(3000)).isEqualTo(a)          // one 3,024-byte hole where a, b and c were
        assertThat(heap.syscalls).hasSize(1)                // only the first brk
    }

    @Test
    fun `free holes that are all too small make the heap grow anyway`() {
        val heap = Heap()
        val blocks = (0 until 128).map { heap.malloc(1000) }
        blocks.filterIndexed { i, _ -> i % 2 == 0 }.forEach(heap::free)   // 64 holes of 1,008 bytes
        heap.malloc(4000)                                   // no hole fits, but the top chunk does
        assertThat(heap.syscalls).hasSize(1)
        val freeBefore = heap.freeBytes
        heap.malloc(4000)                                   // no hole fits and the top chunk is used up

        assertThat(freeBefore).isGreaterThan(64 * 1008L)
        assertThat(heap.syscalls).hasSize(2)
        assertThat(heap.syscalls.last()).startsWith("brk +")
    }

    @Test
    fun `freeing everything but the last block keeps all of RSS, like frag_c`() {
        val real = fragRun(1)                               // frag.c 200000: keep only the last block
        val baseline = real.last().first                    // RSS once everything is freed: libc, stack, the pointer array
        val heap = Heap()
        val blocks = (0 until 200_000).map { heap.malloc(1000) }
        assertThat(heap.heapBytes / mb).isEqualTo(real[1].second)       // 192 MB of heap
        assertThat(heap.rssBytes / mb).isBetween(real[1].first - baseline - 1, real[1].first - baseline + 1)

        blocks.dropLast(1).forEach(heap::free)
        assertThat(heap.rssBytes / mb).isBetween(real[2].first - baseline - 1, real[2].first - baseline + 1)
        assertThat(heap.heapBytes / mb).isEqualTo(real[2].second)       // the last block pins the break
        assertThat(heap.freeBytes).isGreaterThan(190 * mb)

        heap.free(blocks.last())                            // now the free space reaches the top: brk moves down
        assertThat(heap.heapBytes / mb).isEqualTo(real[4].second)
        assertThat(heap.rssBytes).isLessThan(mb)
        assertThat(heap.syscalls.last()).startsWith("brk -")
    }

    @Test
    fun `malloc_trim gives back the whole pages inside free chunks, like frag_c 32`() {
        val real = fragRun(0)                               // frag.c 32: keep every 32nd block
        val baseline = real.last().first
        val heap = Heap()
        val blocks = (0 until 200_000).map { heap.malloc(1000) }
        blocks.filterIndexed { i, _ -> i % 32 != 31 }.forEach(heap::free)
        assertThat(heap.liveChunks).isEqualTo(6250)
        assertThat(heap.rssBytes / mb).isBetween(real[2].first - baseline - 1, real[2].first - baseline + 1)

        heap.trim()                                         // 31 free chunks in a row hold 6 or 7 whole pages
        assertThat(heap.rssBytes / mb).isBetween(real[3].first - baseline - 2, real[3].first - baseline + 1)
        assertThat(heap.heapBytes / mb).isEqualTo(real[3].second)       // the addresses stay; only the RAM went
    }

    /** arenas.c: thread 0 prints, threads 1..16 malloc at once, then each builds 16 MB and frees all but one block. */
    private fun replayArenas(arenaMax: Int): Arenas {
        val a = Arenas(cpus = 12, arenaMax = arenaMax)
        a.malloc(0, 4096)                                   // stdout's buffer, on the main thread
        for (t in 1..16) repeat(100) { a.free(a.malloc(t, 4000)) }
        for (t in 1..16) {
            val blocks = (0 until 4096).map { a.malloc(t, 4000) }
            blocks.dropLast(1).forEach(a::free)
        }
        return a
    }

    @Test
    fun `replaying arenas_c shows each arena keeping its own freed memory`() {
        val real = Captured.lines("/sfz/os/l08/arenas.txt").filter { it.startsWith("each thread") }.map { line ->
            val (arenas, rss, vsz) = Regex("""arenas (\d+), RSS (\d+) MB, VSZ (\d+) MB""").find(line)!!.destructured
            Triple(arenas.toInt(), rss.toLong(), vsz.toLong())
        }
        val models = listOf(0, 2, 1).map(::replayArenas)
        for ((model, captured) in models.zip(real)) {
            assertThat(model.heaps).hasSize(captured.first)                 // 17, 2, 1
            assertThat(model.rssBytes / mb).isBetween(captured.second - 4, captured.second)   // 253, 33, 17 MB
        }
        // 16 extra arenas reserve 64 MB of address space each: the VSZ gap between the default run and one arena
        val modelGap = (models[0].reservedBytes - models[2].reservedBytes) / mb
        assertThat(modelGap).isBetween(real[0].third - real[2].third - 4, real[0].third - real[2].third + 4)
    }

    @Test
    fun `MALLOC_ARENA_MAX caps the arenas and later threads share them round robin`() {
        assertThat(Arenas(cpus = 12).limit).isEqualTo(96)
        val a = Arenas(cpus = 12, arenaMax = 2)
        val main = a.arenaFor(0)
        val first = a.arenaFor(1)                           // a new arena: there is room for one more
        assertThat(first).isNotSameAs(main)
        assertThat(listOf(2, 3, 4, 5).map(a::arenaFor)).containsExactly(main, first, main, first)
        assertThat(a.arenaFor(3)).isSameAs(first)           // a thread keeps the arena it got
        assertThat(a.heaps).hasSize(2)
    }
}
