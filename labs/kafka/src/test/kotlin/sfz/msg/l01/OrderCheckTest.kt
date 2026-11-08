package sfz.msg.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

class OrderCheckTest {
    private fun log(vararg entries: Pair<String, Int>) = entries.map { (k, s) -> Message(k, s) }

    @Test
    fun `a log in order has no duplicates and no inversions`() {
        val r = OrderCheck.check(log("a" to 1, "a" to 2, "a" to 3))
        assertThat(r).isEqualTo(OrderCheck.Result(3, 0, 0))
    }

    @Test
    fun `m3 after m4 is one inversion`() {
        val r = OrderCheck.check(log("a" to 1, "a" to 2, "a" to 4, "a" to 3, "a" to 5))
        assertThat(r).isEqualTo(OrderCheck.Result(5, 0, 1))
    }

    @Test
    fun `a message processed twice is a duplicate, not an inversion`() {
        val r = OrderCheck.check(log("a" to 1, "a" to 2, "a" to 2, "a" to 3))
        assertThat(r).isEqualTo(OrderCheck.Result(4, 1, 0))
    }

    @Test
    fun `a late message is an inversion the first time and a duplicate after that`() {
        val r = OrderCheck.check(log("a" to 1, "a" to 3, "a" to 2, "a" to 3, "a" to 2))
        assertThat(r).isEqualTo(OrderCheck.Result(5, 2, 1))
    }

    @Test
    fun `keys are checked separately, so interleaving two accounts is fine`() {
        val r = OrderCheck.check(log("a" to 1, "b" to 7, "a" to 2, "b" to 8, "b" to 9, "a" to 3))
        assertThat(r.inversions()).isZero()
        assertThat(r.duplicates()).isZero()
    }

    @Test
    fun `an inversion does not lower the mark it is checked against`() {
        // after 5, both 3 and 4 are late, even though 4 > 3
        val r = OrderCheck.check(log("a" to 1, "a" to 5, "a" to 3, "a" to 4))
        assertThat(r.inversions()).isEqualTo(2)
    }
}
