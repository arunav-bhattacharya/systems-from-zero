package sfz.stream.l08

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.bigdata.support.Streams.at
import java.time.Duration

class WindowedCounterTest {
    private fun counter() = WindowedCounter(size = Duration.ofMinutes(5), delay = Duration.ofMinutes(10))
    private fun w(start: String, end: String) = Window(at(start), at(end))
    private fun batch(c: WindowedCounter, vararg times: String) = c.batch(times.map(::at))

    @Test
    fun `windows are 5 minutes long, start on multiples of 5, include their start and exclude their end`() {
        val c = counter()
        assertThat(c.windowOf(at("10:03"))).isEqualTo(w("10:00", "10:05"))
        assertThat(c.windowOf(at("10:04:59"))).isEqualTo(w("10:00", "10:05"))
        assertThat(c.windowOf(at("10:05"))).isEqualTo(w("10:05", "10:10"))
    }

    @Test
    fun `the watermark is the latest event time seen minus the delay, and never moves back`() {
        val c = counter()
        assertThat(batch(c, "10:01", "10:06", "10:02")).isEmpty()
        assertThat(c.watermark).isEqualTo(at("09:56"))
        batch(c, "10:03")                                   // older than 10:06: the watermark stays
        assertThat(c.watermark).isEqualTo(at("09:56"))
        batch(c, "10:14")
        assertThat(c.watermark).isEqualTo(at("10:04"))
        assertThat(c.open().map { it.window.start }).containsExactly(at("10:00"), at("10:05"), at("10:10"))
    }

    @Test
    fun `a late event is counted while its window is open, even when it is older than the delay`() {
        val c = counter()
        batch(c, "10:01", "10:02", "10:06")
        batch(c, "10:14")                                   // watermark 10:04
        // 10:03 is 11 minutes behind 10:14, but its window ends at 10:05, after the watermark
        assertThat(batch(c, "10:03")).isEmpty()
        assertThat(c.dropped).isZero()
        assertThat(c.open().first()).isEqualTo(WindowCount(w("10:00", "10:05"), 3))
    }

    @Test
    fun `append mode emits a window once, when the watermark reaches its end, and later events for it are dropped`() {
        val c = counter()
        batch(c, "10:01", "10:02", "10:06")
        batch(c, "10:14")
        batch(c, "10:03")
        assertThat(batch(c, "10:21")).describedAs("watermark 10:11").containsExactly(
            WindowCount(w("10:00", "10:05"), 3),
            WindowCount(w("10:05", "10:10"), 1),
        )
        assertThat(batch(c, "10:04", "10:08")).isEmpty()
        assertThat(c.dropped).isEqualTo(2)
        assertThat(batch(c, "10:13")).describedAs("its window ends 10:15, after the watermark").isEmpty()
        assertThat(c.open()).containsExactly(WindowCount(w("10:10", "10:15"), 2), WindowCount(w("10:20", "10:25"), 1))
    }

    @Test
    fun `a window whose end equals the watermark is closed`() {
        val c = counter()
        assertThat(batch(c, "10:01", "10:15")).containsExactly(WindowCount(w("10:00", "10:05"), 1))   // watermark 10:05
        batch(c, "10:04", "10:05")
        assertThat(c.dropped).describedAs("10:04 is in the closed window, 10:05 starts the next").isEqualTo(1)
    }

    @Test
    fun `the watermark a batch sets applies only from the next batch`() {
        val c = counter()
        batch(c, "10:01")
        // 10:02 arrives together with 10:30: it is checked against the old watermark and counted
        assertThat(batch(c, "10:02", "10:30")).containsExactly(WindowCount(w("10:00", "10:05"), 2))
        assertThat(c.watermark).isEqualTo(at("10:20"))
        assertThat(c.dropped).isZero()
    }
}
