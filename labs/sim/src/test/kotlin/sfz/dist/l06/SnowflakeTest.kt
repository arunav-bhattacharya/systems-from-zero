package sfz.dist.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class SnowflakeTest {
    private val start = SnowflakeIds.EPOCH_MS + 1_000_000
    private var wall = start
    private val ids = SnowflakeIds(machine = 7) { wall }

    @Test
    fun `when the wall clock steps back, ids keep growing on the last millisecond`() {
        val before = List(3) { ids.next() }                     // sequences 0, 1, 2 at `start`
        wall = start - 1_000                                    // NTP steps the clock back one second
        val after = List(2) { ids.next() }
        assertThat(before + after).isSorted().doesNotHaveDuplicates()
        assertThat(after.map(SnowflakeIds::timestampOf)).containsOnly(start)
        assertThat(after.map(SnowflakeIds::sequenceOf)).containsExactly(3, 4)
        assertThat(after.map(SnowflakeIds::machineOf)).containsOnly(7)
    }

    @Test
    fun `once the clock passes the last millisecond, ids follow it again`() {
        val first = ids.next()
        wall = start - 1_000
        val held = ids.next()                                   // still on `start`
        wall = start + 1
        val id = ids.next()
        assertThat(listOf(first, held, id)).isSorted().doesNotHaveDuplicates()
        assertThat(SnowflakeIds.timestampOf(id)).isEqualTo(start + 1)
        assertThat(SnowflakeIds.sequenceOf(id)).isZero()
    }

    @Test
    fun `the 4,097th id in one millisecond borrows the next millisecond`() {
        val burst = List(4_097) { ids.next() }                   // the clock doesn't move
        assertThat(burst).isSorted().doesNotHaveDuplicates()
        val last = burst.last()
        assertThat(SnowflakeIds.timestampOf(last)).isEqualTo(start + 1)
        assertThat(SnowflakeIds.sequenceOf(last)).isZero()
        val next = ids.next()                                    // the clock still says `start`
        assertThat(next).isGreaterThan(last)
        assertThat(SnowflakeIds.timestampOf(next)).isEqualTo(start + 1)
    }

    @Test
    fun `ten thousand ids across a one-second step back are unique and increasing`() {
        val made = mutableListOf<Long>()
        for (i in 0 until 10_000) {
            if (i == 4_000) wall -= 1_000                        // the step back lands mid-run
            if (i % 3 == 0) wall++                               // about 3 ids per millisecond
            made += ids.next()
        }
        assertThat(made).isSorted().doesNotHaveDuplicates()
    }
}
