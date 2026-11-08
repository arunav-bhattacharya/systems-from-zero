package sfz.stream.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Lesson stream-04, exercises 1 and 2, in src/main/kotlin/sfz/stream/l04/Windows.kt. */
class WindowsTest {

    private val minute = 60_000L

    @Test
    fun `a tumbling window includes its start and excludes its end`() {
        assertThat(Windows.tumbling(0, minute)).isEqualTo(Window(0, minute))
        assertThat(Windows.tumbling(59_999, minute)).isEqualTo(Window(0, minute))
        assertThat(Windows.tumbling(60_000, minute)).isEqualTo(Window(minute, 2 * minute))
        assertThat(Windows.tumbling(9 * 3_600_000 + 14 * minute + 20_000, minute))   // 09:14:20
            .isEqualTo(Window(9 * 3_600_000 + 14 * minute, 9 * 3_600_000 + 15 * minute))
    }

    @Test
    fun `an event is in size divided by advance hopping windows`() {
        val t = 9 * minute + 20_000                                  // 00:09:20
        val windows = Windows.hopping(t, sizeMs = 5 * minute, advanceMs = minute)
        assertThat(windows).containsExactly(
            Window(5 * minute, 10 * minute),
            Window(6 * minute, 11 * minute),
            Window(7 * minute, 12 * minute),
            Window(8 * minute, 13 * minute),
            Window(9 * minute, 14 * minute),
        )
        assertThat(windows).allMatch { t in it }
    }

    @Test
    fun `hopping windows that would start before zero don't exist, and advance equal to size is tumbling`() {
        assertThat(Windows.hopping(90_000, sizeMs = 5 * minute, advanceMs = minute))
            .containsExactly(Window(0, 5 * minute), Window(minute, 6 * minute))
        assertThat(Windows.hopping(90_000, sizeMs = minute, advanceMs = minute)).containsExactly(Windows.tumbling(90_000, minute))
        assertThat(Windows.hopping(5 * minute, sizeMs = 5 * minute, advanceMs = minute))
            .describedAs("the window that ends at t doesn't hold t").doesNotContain(Window(0, 5 * minute))
    }

    @Test
    fun `sessions end after a silence longer than the gap`() {
        val gap = 30 * minute
        val times = listOf(0L, 10 * minute, 40 * minute, 100 * minute, 105 * minute)
        assertThat(Windows.sessions(times, gap)).containsExactly(
            Windows.Session(0, 40 * minute, 3),                      // gaps of 10 and 30 minutes: one session
            Windows.Session(100 * minute, 105 * minute, 2),          // 60 minutes of silence before it
        )
    }

    @Test
    fun `a late event that lands in the gap merges two sessions`() {
        val gap = 30 * minute
        val onTime = listOf(0L, 20 * minute, 70 * minute, 80 * minute)
        assertThat(Windows.sessions(onTime, gap)).hasSize(2)
        val withLate = onTime + 45 * minute                          // arrives last, happened in the middle
        assertThat(Windows.sessions(withLate, gap)).containsExactly(Windows.Session(0, 80 * minute, 5))
    }
}
