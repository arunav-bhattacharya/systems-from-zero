package sfz.os.l09

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class PageCacheTest {
    private val name = "routing.json"
    private val old = """{"issuer": "acme-bank", "timeoutMs": 120}""".toByteArray()
    private val new = """{"issuer": "acme-bank", "timeoutMs": 250, "retries": 2}""".toByteArray()

    /** A disk that already holds routing.json with the old content, safely: data, size and directory entry. */
    private fun durableDisk(): Disk {
        val k = Kernel()
        val inode = k.create(name)
        k.write(inode, 0, old)
        k.fsync(inode)
        k.fsyncDir()
        return k.crash().disk
    }

    /** What the kernel may have written on its own just before the power went out. */
    private val lastMoments: Map<String, (Kernel) -> Unit> = mapOf(
        "nothing" to {},
        "a journal commit" to { it.commitMetadata() },
        "a data writeback" to { it.writeBackAll() },
        "both" to { it.writeBackAll(); it.commitMetadata() },
    )

    /** Run [action] on a fresh kernel over the durable disk, cut the power after [steps] calls, and reboot. */
    private fun crashAfter(steps: Int, lastMoment: (Kernel) -> Unit, action: (Kernel) -> Unit): ByteArray? {
        val k = Kernel(durableDisk())
        k.powerCutAfter = steps
        try {
            action(k)
        } catch (_: PowerCut) {
        }
        k.powerCutAfter = null
        lastMoment(k)
        return k.crash().disk.contents(name)
    }

    @Test
    fun `write puts the bytes in the page cache and nothing on the disk`() {
        val k = Kernel()
        val inode = k.create("auth.log")
        k.write(inode, 0, ByteArray(10_000) { 7 })              // 3 pages: 4,096 + 4,096 + 1,808 bytes

        assertThat(k.dirtyPages).isEqualTo(3)
        assertThat(k.size(inode)).isEqualTo(10_000)
        assertThat(k.disk.pageWrites).isZero()
        assertThat(k.readAll("auth.log")).containsOnly(7)          // programs see the new bytes at once
        k.write(inode, 4_000, ByteArray(200) { 9 })              // crosses into page 1, both already dirty
        assertThat(k.dirtyPages).isEqualTo(3)
        assertThat(k.read(inode, 3_999, 202).toList()).isEqualTo(listOf<Byte>(7) + List<Byte>(200) { 9 } + listOf<Byte>(7))
    }

    @Test
    fun `a second read of a file comes from the page cache`() {
        val k = Kernel(durableDisk())
        k.readAll(name)
        assertThat(k.cacheMisses).isEqualTo(1)
        k.readAll(name)
        k.readAll(name)
        assertThat(k.cacheMisses).isEqualTo(1)
        assertThat(k.cacheHits).isEqualTo(2)
    }

    @Test
    fun `a crash loses every write that was never written back`() {
        val k = Kernel(durableDisk())
        k.write(k.open(name), 0, new)
        assertThat(k.readAll(name)).isEqualTo(new)               // the write "worked"

        assertThat(k.crash().disk.contents(name)).isEqualTo(old)
    }

    @Test
    fun `fsync puts the file's pages and size on the disk before it returns`() {
        val k = Kernel(durableDisk())
        val inode = k.open(name)
        val flushesBefore = k.disk.flushes
        k.write(inode, 0, new)
        k.fsync(inode)

        assertThat(k.dirtyPages).isZero()
        assertThat(k.disk.flushes - flushesBefore).isEqualTo(1)       // one device flush per fsync
        assertThat(k.crash().disk.contents(name)).isEqualTo(new)
    }

    @Test
    fun `fsync of one file leaves the other files' dirty pages alone`() {
        val k = Kernel()
        val log = k.create("auth.log")
        val batch = k.create("settlement.csv")
        k.write(log, 0, ByteArray(4096))
        k.write(batch, 0, ByteArray(3 * 4096))
        k.fsync(log)

        assertThat(k.dirtyPages).isEqualTo(3)
        assertThat(k.disk.pageWrites).isEqualTo(1)
    }

    @Test
    fun `the flusher writes a page back once it has been dirty for 30 seconds`() {
        val k = Kernel()                                         // flusher every 5 s, pages expire after 30 s
        val inode = k.create("auth.log")
        k.tick(2_000)
        k.write(inode, 0, ByteArray(4096))                       // dirtied at 2 s
        k.tick(30_000)                                           // now 32 s: the 30 s wake-up saw it 28 s old
        assertThat(k.dirtyPages).isEqualTo(1)
        k.tick(3_000)                                            // the 35 s wake-up writes it
        assertThat(k.dirtyPages).isZero()
        assertThat(k.disk.pageWrites).isEqualTo(1)
    }

    @Test
    fun `with the lab box's 15 second flusher a dirty page waits 30 to 45 seconds`() {
        // the lab box's VM: dirty_expire_centisecs = 3000, dirty_writeback_centisecs = 1500
        val waits = (0 until 15).map { phase ->                  // the write can land anywhere between two wake-ups
            val k = Kernel(wakeMs = 15_000)
            k.tick(phase * 1_000L)
            val inode = k.create("batch.csv")
            k.write(inode, 0, ByteArray(16 * 4096))
            var waited = 0L
            while (k.dirtyPages > 0) {
                k.tick(1_000)
                waited += 1
            }
            waited
        }
        assertThat(waits).allMatch { it in 30L..44L }
        assertThat(waits.min()).isEqualTo(30L)                    // written at a wake-up, expired exactly at the next-but-one
        assertThat(waits.max()).isEqualTo(44L)                    // missed by a second: waits a whole extra interval
    }

    @Test
    fun `renaming before fsync can point the name at bytes that never reached the disk`() {
        val k = Kernel(durableDisk())
        val tmp = k.create("$name.tmp")
        k.write(tmp, 0, new)
        k.rename("$name.tmp", name)                              // no fsync of the new file first
        k.tick(5_000)                                            // the journal commits the rename and the size

        val after = k.crash().disk.contents(name)!!
        assertThat(after).hasSize(new.size).containsOnly(0)      // the right length, all zeros
    }

    @Test
    fun `overwriting in place can leave an empty file after a crash`() {
        val outcomes = (0..4).flatMap { steps ->
            lastMoments.values.map { crashAfter(steps, it) { k -> Config.overwrite(k, name, new) }?.toList() }
        }.toSet()
        assertThat(outcomes).contains(emptyList())                // truncated, then the power went out
        assertThat(outcomes).contains(old.toList(), new.toList())
    }

    @Test
    fun `replace leaves the old file or the new one at every crash point`() {
        for (steps in 0..6) {
            for ((moment, lastMoment) in lastMoments) {
                val after = crashAfter(steps, lastMoment) { k -> Config.replace(k, name, new) }
                assertThat(after?.toList())
                    .describedAs("power cut after $steps calls, with $moment just before")
                    .isIn(old.toList(), new.toList())
            }
        }
    }

    @Test
    fun `once replace returns, the new file survives a crash`() {
        val k = Kernel(durableDisk())
        Config.replace(k, name, new)

        assertThat(k.crash().disk.contents(name)).isEqualTo(new)    // even if the kernel wrote nothing else
        assertThat(k.disk.flushes).isEqualTo(4)                     // two in durableDisk, two in replace
    }
}
