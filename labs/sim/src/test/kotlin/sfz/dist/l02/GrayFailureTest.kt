package sfz.dist.l02

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

/** Exercise 3, [chanceToTouchGray]: one gray path among [paths] equal ones. */
class GrayFailureTest {
    @Test
    fun `a single request touches the gray path one time in n`() {
        assertThat(chanceToTouchGray(paths = 16, fanOut = 1)).isCloseTo(1.0 / 16, within(1e-12))
        assertThat(chanceToTouchGray(paths = 1, fanOut = 1)).isEqualTo(1.0)
        assertThat(chanceToTouchGray(paths = 16, fanOut = 0)).isEqualTo(0.0)
    }

    @Test
    fun `a request that fans out to 100 servers almost always touches it`() {
        assertThat(chanceToTouchGray(paths = 16, fanOut = 100)).isCloseTo(0.99843, within(1e-5))
        assertThat(chanceToTouchGray(paths = 64, fanOut = 100)).isCloseTo(0.79296, within(1e-5))
    }

    @Property(tries = 200)
    fun `more fan-out never lowers the chance`(
        @ForAll @IntRange(min = 1, max = 256) paths: Int,
        @ForAll @IntRange(min = 0, max = 1_000) fanOut: Int,
    ) {
        val p = chanceToTouchGray(paths, fanOut)
        assertThat(p).isBetween(0.0, 1.0)
        assertThat(chanceToTouchGray(paths, fanOut + 1)).isGreaterThanOrEqualTo(p)
    }
}
