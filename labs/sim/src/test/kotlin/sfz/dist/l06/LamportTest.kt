package sfz.dist.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class LamportTest {
    @Test
    fun `every local event and every send adds one`() {
        val clock = LamportClock(node = 2)
        assertThat(clock.local()).isEqualTo(Stamp(1, 2))
        assertThat(clock.send()).isEqualTo(Stamp(2, 2))
        assertThat(clock.counter).isEqualTo(2)
    }

    @Test
    fun `a receive jumps past the sender's counter`() {
        val behind = LamportClock(node = 1)
        behind.local()                                       // counter 1
        assertThat(behind.receive(Stamp(7, 0))).isEqualTo(Stamp(8, 1))
        val ahead = LamportClock(node = 1)
        repeat(10) { ahead.local() }                         // counter 10
        assertThat(ahead.receive(Stamp(7, 0))).isEqualTo(Stamp(11, 1))
    }

    @Test
    fun `stamps order by counter, then by node`() {
        assertThat(Stamp(1, 3)).isLessThan(Stamp(2, 0))
        assertThat(Stamp(4, 0)).isLessThan(Stamp(4, 1))
        assertThat(listOf(Stamp(2, 1), Stamp(1, 2), Stamp(1, 0)).sorted())
            .containsExactly(Stamp(1, 0), Stamp(1, 2), Stamp(2, 1))
    }

    @Test
    fun `an authorization and its capture keep their order with clocks 40 ms apart`() {
        // pay-81723: node 0 authorizes and tells node 1, which captures; node 1's wall clock is 40 ms behind
        val h = History(
            nodes = 2,
            events = listOf(
                Event(0, node = 0, kind = Kind.SEND, realTime = 100, physical = 140, msg = 0),
                Event(1, node = 1, kind = Kind.RECEIVE, realTime = 105, physical = 105, msg = 0),
                Event(2, node = 1, kind = Kind.LOCAL, realTime = 106, physical = 106),
            ),
            offsets = listOf(40, 0),
            steps = emptyList(),
        )
        val stamps = lamportStamps(h)
        assertThat(h.events[2].physical).isLessThan(h.events[0].physical)    // the wall clocks get it backwards
        assertThat(stamps[0]).isLessThan(stamps[2])                          // Lamport doesn't
    }
}
