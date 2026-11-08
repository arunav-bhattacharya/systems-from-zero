package sfz.stream.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Nested
import org.junit.jupiter.api.Test

/**
 * Lesson stream-04, exercise 3, in src/main/kotlin/sfz/stream/l04/WindowedCounter.kt, plus the
 * redeploy spike, which needs exercise 1a (Windows.tumbling).
 */
class TimeTest {

    private fun run(events: List<Event>, sizeMs: Long, graceMs: Long): WindowedCounter =
        WindowedCounter(sizeMs, graceMs).apply { events.forEach(::onEvent); flush() }

    @Nested
    inner class `the redeploy` {
        private val events = Scenario.redeploy()

        @Test
        fun `counted by processing time, the redeploy looks like a 20x spike`() {
            val perSecond = countPerWindow(events, 1_000) { it.processingTime }
            assertThat(perSecond[Window(119_000, 120_000)]).describedAs("the processor was stopped").isNull()
            assertThat(perSecond.getValue(Window(120_000, 121_000))).isEqualTo(2_000)
            assertThat(perSecond.getValue(Window(121_000, 122_000))).isEqualTo(2_000)
            assertThat(perSecond.getValue(Window(122_000, 123_000))).isEqualTo(2_000)
            assertThat(perSecond.values.max()).isEqualTo(2_000)
        }

        @Test
        fun `counted by event time, it is 100 a second all the way through`() {
            val perSecond = countPerWindow(events, 1_000) { it.eventTime }
            assertThat(perSecond).hasSize(180)
            assertThat(perSecond.values).containsOnly(100)
        }

        @Test
        fun `a watermark over the drained backlog drops nothing, because the backlog comes in order`() {
            val counter = run(events, sizeMs = 1_000, graceMs = 0)
            assertThat(counter.lateDropped).isEqualTo(0)
            assertThat(counter.results).hasSize(180)
            assertThat(counter.results.map { it.count }).containsOnly(100)
        }
    }

    @Nested
    inner class `three stragglers` {
        private val events = Scenario.stragglers()

        @Test
        fun `with no grace all three late events are dropped`() {
            val c = run(events, sizeMs = 60_000, graceMs = 0)
            assertThat(c.lateDropped).isEqualTo(3)
            assertThat(c.results.map { it.count }).containsExactly(60, 60, 60, 60, 60)
        }

        @Test
        fun `10 seconds of grace keeps the one that was 5 seconds past its window`() {
            val c = run(events, sizeMs = 60_000, graceMs = 10_000)
            assertThat(c.lateDropped).isEqualTo(2)
            assertThat(c.results.first()).isEqualTo(WindowedCounter.Result("m-7", Window(0, 60_000), 61, 70_000))
        }

        @Test
        fun `60 seconds of grace keeps two, and the first window waits a minute longer`() {
            val c = run(events, sizeMs = 60_000, graceMs = 60_000)
            assertThat(c.lateDropped).isEqualTo(1)                    // 90 s past its window: still too late
            assertThat(c.results.map { it.count }).containsExactly(61, 61, 60, 60, 60)
            assertThat(c.results.first().emittedAtWatermark).isEqualTo(120_000)
        }

        @Test
        fun `a window is emitted once the watermark reaches its end plus the grace`() {
            val c = WindowedCounter(sizeMs = 60_000, graceMs = 0)
            events.takeWhile { it.eventTime < 60_000 }.forEach(c::onEvent)
            assertThat(c.watermark).isEqualTo(59_000)
            assertThat(c.results).describedAs("the window 0-60 s might still get events").isEmpty()
            c.onEvent(Event("m-7", 60_000, 60_000))
            assertThat(c.results).containsExactly(WindowedCounter.Result("m-7", Window(0, 60_000), 60, 60_000))
        }

        @Test
        fun `the flush emits the windows the stream never closed`() {
            val c = WindowedCounter(sizeMs = 60_000, graceMs = 60_000)
            events.forEach(c::onEvent)
            assertThat(c.results.map { it.window.start }).containsExactly(0L, 60_000L, 120_000L)
            c.flush()
            assertThat(c.results.map { it.window.start }).containsExactly(0L, 60_000L, 120_000L, 180_000L, 240_000L)
            assertThat(c.results.takeLast(2).map { it.emittedAtWatermark }).containsOnly(299_000)
        }
    }

    @Nested
    inner class `out-of-order arrival` {
        private val events = Scenario.jittered(seed = 42, maxDelayMs = 2_000)

        @Test
        fun `with no grace, many events miss their window`() {
            val inversions = events.zipWithNext().count { (a, b) -> b.eventTime < a.eventTime }
            assertThat(inversions).describedAs("a later event often arrives first").isGreaterThan(1_000)
            val c = run(events, sizeMs = 1_000, graceMs = 0)
            assertThat(c.lateDropped).isGreaterThan(500)
            assertThat(c.results.sumOf { it.count } + c.lateDropped).isEqualTo(events.size)
        }

        @Test
        fun `grace as long as the worst delay drops nothing, and the counts match a batch count by event time`() {
            val c = run(events, sizeMs = 1_000, graceMs = 2_000)
            assertThat(c.lateDropped).isEqualTo(0)
            val batch = events.groupingBy { it.key to Windows.tumbling(it.eventTime, 1_000) }.eachCount()
            assertThat(c.results.associate { (it.key to it.window) to it.count }).isEqualTo(batch)
        }

        @Test
        fun `more grace never drops more`() {
            val drops = listOf(0L, 250, 500, 1_000, 1_500, 2_000).map { run(events, 1_000, it).lateDropped }
            assertThat(drops).isSortedAccordingTo(Comparator.reverseOrder())
            assertThat(drops.last()).isEqualTo(0)
        }
    }
}
