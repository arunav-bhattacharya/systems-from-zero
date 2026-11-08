package sfz.repl.l05

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class ConflictsTest {
    private fun write(id: String, ts: Long, vararg seen: String, holds: Set<String> = setOf(id)) =
        Write(id, id.substringBefore(':'), holds, ts, seen.toSet())

    @Test
    fun `last write wins keeps the higher timestamp, and the region name breaks a tie`() {
        val eu = write("eu:1", 1_000)
        val us = write("us:1", 1_040)
        assertThat(lastWriteWins(eu, us)).isEqualTo(us)
        assertThat(lastWriteWins(us, eu)).isEqualTo(us)
        // same millisecond on both clocks: "us" > "eu", on every region, whichever arrives first
        val tie = write("us:2", 1_000)
        assertThat(lastWriteWins(eu, tie)).isEqualTo(tie)
        assertThat(lastWriteWins(tie, eu)).isEqualTo(tie)
    }

    @Test
    fun `order follows what each writer had seen, never the clock`() {
        val eu1 = write("eu:1", 0)
        // us:1 is an hour later by the clock, but us never heard of eu:1: concurrent
        val us1 = write("us:1", 3_600_000)
        assertThat(order(eu1, us1)).isEqualTo(Order.CONCURRENT)
        assertThat(order(us1, eu1)).isEqualTo(Order.CONCURRENT)
        // us:2 is one millisecond after eu:2 and had seen it: ordered, with no conflict
        val eu2 = write("eu:2", 5_000, "eu:1")
        val us2 = write("us:2", 5_001, "eu:1", "eu:2", "us:1")
        assertThat(order(eu2, us2)).isEqualTo(Order.BEFORE)
        assertThat(order(us2, eu2)).isEqualTo(Order.AFTER)
        assertThat(order(us2, us2.copy())).isEqualTo(Order.SAME)
        // a clock that runs behind doesn't change the answer: us:3 saw eu:3 despite its smaller timestamp
        val eu3 = write("eu:3", 9_000, "eu:1", "eu:2")
        val us3 = write("us:3", 8_800, "eu:1", "eu:2", "eu:3", "us:1", "us:2")
        assertThat(order(eu3, us3)).isEqualTo(Order.BEFORE)
    }

    @Test
    fun `the detector ignores a message that a newer version already includes, and a repeat`() {
        val eu1 = write("eu:1", 0)
        val eu2 = write("eu:2", 10, "eu:1", holds = setOf("eu:1", "eu:2"))
        val old = applyDetecting(listOf(eu2), eu1) // eu:1 overtaken in the network by eu:2
        assertThat(old).isEqualTo(Applied(listOf(eu2), conflict = false))
        val repeat = applyDetecting(listOf(eu2), eu2.copy())
        assertThat(repeat).isEqualTo(Applied(listOf(eu2), conflict = false))
    }

    @Test
    fun `the detector replaces what the incoming write saw and keeps concurrent writes as siblings`() {
        val eu1 = write("eu:1", 0)
        val us1 = write("us:1", 0)
        val both = applyDetecting(listOf(eu1), us1)
        assertThat(both).isEqualTo(Applied(listOf(eu1, us1), conflict = true))

        // a client read both siblings, merged them, and wrote: its write replaces both
        val merged = write("eu:2", 50, "eu:1", "us:1", holds = setOf("eu:1", "us:1", "eu:2"))
        assertThat(applyDetecting(both.versions, merged)).isEqualTo(Applied(listOf(merged), conflict = false))

        // a write that saw eu:1 but not us:1 replaces eu:1 and stays next to us:1
        val eu2 = write("eu:2", 50, "eu:1")
        assertThat(applyDetecting(both.versions, eu2)).isEqualTo(Applied(listOf(us1, eu2), conflict = true))
    }

    @Test
    fun `two regions accept a write at the same moment and last write wins drops one`() {
        val r = simulate(Resolution.LAST_WRITE_WINS, script = listOf("eu" to 0L, "us" to 0L), delayMs = 35L..35L)
        assertThat(r.acknowledged).isEqualTo(2)
        assertThat(r.converged).isTrue()
        // both clocks read 0, so the tie goes to "us": eu's acknowledged hold is gone everywhere
        assertThat(r.finalHolds).containsExactly("us:1")
        assertThat(r.lost).containsExactly("eu:1")
        assertThat(r.conflicts).isZero()
    }

    @Test
    fun `the detector keeps both writes from the same moment as siblings`() {
        val r = simulate(Resolution.DETECT_CONFLICTS, script = listOf("eu" to 0L, "us" to 0L), delayMs = 35L..35L)
        assertThat(r.converged).isTrue()
        assertThat(r.finalHolds).containsExactly("eu:1", "us:1")
        assertThat(r.lost).isEmpty()
        assertThat(r.conflicts).isEqualTo(2) // found once in each region
    }

    @Test
    fun `messages that overtake each other lose nothing when only one region writes`() {
        // eu writes ten times, 5 ms apart; one-way delays of 20 to 80 ms reorder them on the way to us
        val script = (0 until 10).map { "eu" to it * 5L }
        for (resolution in Resolution.entries) {
            val r = simulate(resolution, script = script, seed = 3)
            assertThat(r.reordered).`as`("$resolution: some messages arrived out of order").isPositive()
            assertThat(r.lost).`as`("$resolution").isEmpty()
            assertThat(r.converged).`as`("$resolution").isTrue()
        }
    }

    @Test
    fun `a region whose clock runs behind loses a write that had seen everything`() {
        // us writes at 0; eu hears of it at 35 ms and writes at 100 ms, but eu's clock is 200 ms behind
        val script = listOf("us" to 0L, "eu" to 100L)
        val skew = mapOf("eu" to -200L)
        val lww = simulate(Resolution.LAST_WRITE_WINS, script = script, delayMs = 35L..35L, skewMs = skew)
        // eu's write is stamped -100, us's is stamped 0: the newer write loses, with no concurrency at all
        assertThat(lww.lost).containsExactly("eu:1")
        val detect = simulate(Resolution.DETECT_CONFLICTS, script = script, delayMs = 35L..35L, skewMs = skew)
        assertThat(detect.lost).isEmpty()
        assertThat(detect.conflicts).isZero()
        assertThat(detect.finalHolds).containsExactly("eu:1", "us:1")
    }

    @Test
    fun `under steady traffic in both regions last write wins converges and loses acknowledged writes`() {
        val r = simulate(Resolution.LAST_WRITE_WINS, writesPerRegion = 300, meanGapMs = 50.0, seed = 42)
        assertThat(r.acknowledged).isEqualTo(600)
        assertThat(r.converged).isTrue()
        // writes 50 ms apart against 20 to 80 ms of lag: most read-modify-writes race one from the other region
        assertThat(r.lost.size).isGreaterThan(150)
        assertThat(r.finalHolds.size + r.lost.size).isEqualTo(600)
    }

    @Test
    fun `the same traffic with the detector converges, loses nothing and counts its conflicts`() {
        val r = simulate(Resolution.DETECT_CONFLICTS, writesPerRegion = 300, meanGapMs = 50.0, seed = 42)
        assertThat(r.converged).isTrue()
        assertThat(r.lost).isEmpty()
        assertThat(r.conflicts).isGreaterThan(100)
        // the price: a write carries the id of nearly every write before it
        assertThat(r.largestHistory).isGreaterThan(590)
    }

    @Property(tries = 30)
    fun `with any seed and two to four regions the detector loses nothing and converges`(
        @ForAll seed: Long,
        @ForAll @IntRange(min = 2, max = 4) regions: Int,
    ) {
        val names = listOf("ap", "eu", "sa", "us").take(regions)
        val r = simulate(Resolution.DETECT_CONFLICTS, regions = names, writesPerRegion = 40, meanGapMs = 30.0, seed = seed)
        assertThat(r.converged).isTrue()
        assertThat(r.lost).isEmpty()
        assertThat(r.finalHolds).hasSize(40 * regions)
    }
}
