package sfz.dist.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class HybridTest {
    private var wall = 0L
    private val clock = HybridClock(node = 0) { wall }

    @Test
    fun `with no messages it reads the wall clock`() {
        wall = 1_000
        assertThat(clock.local()).isEqualTo(Hlc(1_000, 0))
        wall = 1_007
        assertThat(clock.send()).isEqualTo(Hlc(1_007, 0))
    }

    @Test
    fun `two events in the same millisecond differ in the counter`() {
        wall = 1_000
        assertThat(clock.local()).isEqualTo(Hlc(1_000, 0))
        assertThat(clock.local()).isEqualTo(Hlc(1_000, 1))
        assertThat(clock.local()).isEqualTo(Hlc(1_000, 2))
    }

    @Test
    fun `a message from a clock that runs ahead pulls l forward and continues its count`() {
        wall = 1_000
        clock.local()
        assertThat(clock.receive(Hlc(1_040, 3))).isEqualTo(Hlc(1_040, 4))   // the sender's l wins
        wall = 1_010
        assertThat(clock.local()).isEqualTo(Hlc(1_040, 5))                  // still ahead of my wall clock
        wall = 1_041
        assertThat(clock.local()).isEqualTo(Hlc(1_041, 0))                  // my wall clock caught up
    }

    @Test
    fun `on a receive, each possible winner sets the counter its own way`() {
        wall = 1_000
        clock.local()
        clock.local()                                                       // (1000,1)
        assertThat(clock.receive(Hlc(1_000, 5))).isEqualTo(Hlc(1_000, 6))   // both l equal: max(1, 5) + 1
        assertThat(clock.receive(Hlc(990, 9))).isEqualTo(Hlc(1_000, 7))     // mine won: my c + 1
        wall = 1_200
        assertThat(clock.receive(Hlc(1_100, 2))).isEqualTo(Hlc(1_200, 0))   // the wall clock won: 0
    }

    @Test
    fun `a wall clock that steps back doesn't pull the stamps back`() {
        wall = 5_000
        val before = clock.local()
        wall = 4_000                                                        // NTP stepped the clock back 1 s
        val after = listOf(clock.local(), clock.local(), clock.send())
        assertThat(after).allSatisfy { assertThat(it).isGreaterThan(before) }
        assertThat(after.map { it.l }).containsOnly(5_000)
        assertThat(after).isSorted()
    }

    @Test
    fun `packing keeps l in the top 48 bits and c in the low 16, in the same order`() {
        val a = Hlc(1_767_225_600_123, 0)
        val b = Hlc(1_767_225_600_123, 65_535)
        val c = Hlc(1_767_225_600_124, 0)
        assertThat(a.pack()).isEqualTo(1_767_225_600_123L shl 16)
        assertThat(Hlc.unpack(b.pack())).isEqualTo(b)
        assertThat(Hlc.unpack(c.pack())).isEqualTo(c)
        assertThat(listOf(a.pack(), b.pack(), c.pack())).isSorted()
    }
}
