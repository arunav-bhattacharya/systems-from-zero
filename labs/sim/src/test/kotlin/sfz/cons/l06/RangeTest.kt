package sfz.cons.l06

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout

@Timeout(10)
class RangeTest {
    private fun range() = Range("payouts").apply {
        load("batch", 0)
        putIntent(1, "batch", 1, ts = 100); resolve(1)
        putIntent(2, "batch", 2, ts = 200); resolve(2)
        putIntent(3, "batch", 3, ts = 300); resolve(3)
    }

    @Test
    fun `a read returns the newest committed version at or below its timestamp`() {
        val r = range()
        assertThat(r.read("batch", readTs = 250, limit = 250)).isEqualTo(Value(2, 200))
        assertThat(r.read("batch", readTs = 200, limit = 200)).`as`("at exactly its timestamp").isEqualTo(Value(2, 200))
        assertThat(r.read("batch", readTs = 50, limit = 50)).`as`("before every commit").isEqualTo(Value(0, 0))
        assertThat(r.read("batch", readTs = 999, limit = 999)).isEqualTo(Value(3, 300))
    }

    @Test
    fun `a committed version inside the uncertainty window can't be placed`() {
        val r = range()
        assertThat(r.read("batch", readTs = 150, limit = 210)).`as`("200 may have happened before the read")
            .isEqualTo(Uncertain(200))
        assertThat(r.read("batch", readTs = 150, limit = 400)).`as`("the highest uncertain one, so one restart is enough")
            .isEqualTo(Uncertain(300))
        assertThat(r.read("batch", readTs = 150, limit = 199)).`as`("above the window: surely in the future")
            .isEqualTo(Value(1, 100))
    }

    @Test
    fun `an intent at or below the top of the window blocks the read until it resolves`() {
        val r = range()
        r.putIntent(4, "batch", 4, ts = 400)
        assertThat(r.read("batch", readTs = 450, limit = 450)).isEqualTo(Blocked(4))
        assertThat(r.read("batch", readTs = 390, limit = 410)).`as`("it may commit inside the window").isEqualTo(Blocked(4))
        assertThat(r.read("batch", readTs = 350, limit = 399)).`as`("an intent above the window can't matter")
            .isEqualTo(Value(3, 300))
        r.resolve(4)
        assertThat(r.read("batch", readTs = 450, limit = 450)).isEqualTo(Value(4, 400))
    }
}
