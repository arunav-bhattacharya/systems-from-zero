package sfz.os.l04

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test
import sfz.os.support.Captured

class SchedulerTest {
    /** One line of spin.c output from the lab box: what the real kernel gave each loop. */
    data class Measured(val nice: Int, val cpuSeconds: Double, val wallSeconds: Double, val switchedOut: Int) {
        val share get() = cpuSeconds / wallSeconds
    }

    private val line = Regex("""nice\s+(-?\d+): ([\d.]+) s of CPU in ([\d.]+) s \(\d+%\), switched out (\d+) times""")

    // two spin loops pinned to one CPU in the lab box, in pairs: nice 0/10, nice 0/5, nice 0/0
    private val measured = Captured.lines("/sfz/os/l04/spin-nice.txt").mapNotNull { line.find(it) }.map {
        val (nice, cpu, wall, out) = it.destructured
        Measured(nice.toInt(), cpu.toDouble(), wall.toDouble(), out.toInt())
    }.chunked(2)

    private fun tenSeconds(scheduler: Scheduler, vararg tasks: Task) = Cpu(scheduler).run(tasks.toList(), 10_000.0)

    @Test
    fun `expected shares come from the weight ratio, never from the nice number itself`() {
        val tenApart = Nice.expectedShares(listOf(0, 10))
        assertThat(tenApart[0]).isCloseTo(0.903, within(0.001))
        assertThat(tenApart[1]).isCloseTo(0.097, within(0.001))
        assertThat(Nice.expectedShares(listOf(0, 5))[0]).isCloseTo(0.754, within(0.001))
        assertThat(Nice.expectedShares(listOf(0, 0, 0))).allSatisfy { assertThat(it).isCloseTo(1.0 / 3, within(1e-9)) }
        // nice 10 against nice 15 is the same 1.25^5 ratio as nice 0 against nice 5
        assertThat(Nice.expectedShares(listOf(10, 15))[0]).isCloseTo(0.753, within(0.005))
    }

    @Test
    fun `round robin gives everyone the same share, whatever their nice value`() {
        val t = tenSeconds(RoundRobin(), Task("a", 0), Task("b", 10))
        assertThat(t.share("a")).isCloseTo(0.5, within(0.001))
        assertThat(t.share("b")).isCloseTo(0.5, within(0.001))
        assertThat(t.order(6)).isEqualTo("ababab")
    }

    @Test
    fun `weighted fair charges virtual time at 1024 divided by weight`() {
        val wf = WeightedFair()
        val normal = Task("normal", 0)
        val batch = Task("batch", 10)
        wf.charge(normal, 10.0, listOf(normal, batch))
        wf.charge(batch, 10.0, listOf(normal, batch))
        assertThat(normal.vruntime).isCloseTo(10.0, within(1e-9))
        assertThat(batch.vruntime).isCloseTo(10.0 * 1024 / 110, within(1e-9))   // 93.1 ms: its clock runs 9.3 times faster
        assertThat(wf.pick(listOf(normal, batch))).isSameAs(normal)
    }

    @Test
    fun `weighted fair splits one CPU like the lab box did`() {
        for ((pair, other) in listOf(0 to 10, 1 to 5, 2 to 0)) {
            val t = tenSeconds(WeightedFair(), Task("a", 0), Task("b", other))
            val (real0, realOther) = measured[pair]
            assertThat(realOther.nice).isEqualTo(other)
            assertThat(t.share("a")).`as`("nice 0 against nice $other").isCloseTo(real0.share, within(0.015))
            assertThat(t.share("b")).`as`("nice $other against nice 0").isCloseTo(realOther.share, within(0.015))
        }
    }

    @Test
    fun `eevdf picks only eligible tasks, even when an ineligible one has the earlier deadline`() {
        val ev = Eevdf()
        val a = Task("a", 0).apply { vruntime = 12.0; deadline = 15.0 }
        val b = Task("b", 5).apply { vruntime = 9.17; deadline = 18.3 }
        // V = (1024 * 12 + 335 * 9.17) / 1359 = 11.3, so a has run ahead and is not owed anything
        assertThat(ev.average(listOf(a, b))).isCloseTo(11.30, within(0.01))
        assertThat(ev.eligible(a, listOf(a, b))).isFalse()
        assertThat(ev.eligible(b, listOf(a, b))).isTrue()
        assertThat(ev.pick(listOf(a, b))).isSameAs(b)

        a.vruntime = 6.0; a.deadline = 9.0                                    // now a is behind V, and its deadline is first
        assertThat(ev.pick(listOf(a, b))).isSameAs(a)
    }

    @Test
    fun `eevdf runs nice 0 against nice 5 in the order the stepper shows`() {
        val a = Task("A", 0)
        val b = Task("B", 5)
        val t = Cpu(Eevdf()).run(listOf(a, b), 18.0)
        assertThat(t.order(6)).isEqualTo("ABAAAB")
        assertThat(a.deadline).isCloseTo(15.0, within(1e-6))                   // A has used 4 slices: vruntime 12, next deadline 15
        assertThat(b.vruntime).isCloseTo(2 * 3.0 * 1024 / 335, within(1e-6))  // B ran twice: 18.3 virtual ms
    }

    @Test
    fun `eevdf keeps the weighted shares and a 3 ms turn for the light task`() {
        val t = tenSeconds(Eevdf(), Task("a", 0), Task("b", 10))
        val (real0, real10) = measured[0]
        assertThat(t.share("a")).isCloseTo(real0.share, within(0.015))
        assertThat(t.share("b")).isCloseTo(real10.share, within(0.015))
        // the nice 10 loop runs one 3 ms slice per turn and waits about 27 ms in between,
        // so it gets switched out a few hundred times in 10 s, like the real loop
        assertThat(t.stretches("b")).allSatisfy { assertThat(it.ms).isCloseTo(3.0, within(1e-9)) }
        assertThat(t.stretches("b").size).isBetween(250, 450)
        assertThat(real10.switchedOut).isBetween(250, 450)
    }

    @Test
    fun `a shorter slice gets the CPU sooner without getting more of it`() {
        fun tasks() = arrayOf(Task("batch-1"), Task("batch-2"), Task("api", sliceMs = 1.0))

        val fair = tenSeconds(WeightedFair(), *tasks())
        val eevdf = tenSeconds(Eevdf(), *tasks())

        assertThat(fair.longestWait("api")).isCloseTo(6.0, within(1e-6))       // a fixed 3 ms slice for everyone
        assertThat(eevdf.longestWait("api")).isLessThanOrEqualTo(3.0 + 1e-6)   // its 1 ms request is honoured
        assertThat(eevdf.share("api")).isCloseTo(1.0 / 3, within(0.005))       // and it still gets a third, not more
        assertThat(eevdf.share("batch-1")).isCloseTo(1.0 / 3, within(0.005))
    }
}
