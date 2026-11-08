package sfz.enc.l03

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test

/** Old code that reads, changes and writes back a document it only half understands. */
class FieldLossTest {
    private val withLanguage = """{"id":7,"name":"customer-7","status":"new","preferredLanguage":"de"}"""

    @Test
    fun `the data-class codec drops a field it doesn't know`() {
        val after = DataClassCodec.touch(withLanguage, "active")
        assertThat(V2.languageOf(after)).isNull()
        // the real assertion of this test is about your codec, below
        assertThat(V2.languageOf(PreservingCodec.touch(withLanguage, "active"))).isEqualTo("de")
    }

    @Test
    fun `the preserving codec changes the status and keeps everything else`() {
        val after = mapper.readTree(PreservingCodec.touch(withLanguage, "active"))
        assertThat(after.get("status").asText()).isEqualTo("active")
        assertThat(after.get("preferredLanguage").asText()).isEqualTo("de")
        assertThat(after.get("name").asText()).isEqualTo("customer-7")
        assertThat(after.size()).isEqualTo(4)
    }

    @Test
    fun `with the data-class codec, loss follows 1 - p^5`() {
        // each of the 5 updates after a customer sets a language has to land on v2 for the language to survive
        for (p in listOf(50, 90, 99)) {
            val expected = 1 - Math.pow(p / 100.0, 5.0)
            assertThat(RollingUpgrade.lossRate(p, DataClassCodec)).describedAs("v2 at $p%").isCloseTo(expected, within(0.04))
        }
        assertThat(RollingUpgrade.lossRate(90, DataClassCodec)).isGreaterThan(0.35)
    }

    @Test
    fun `at 100 percent v2 nothing is lost, whatever v1 does`() {
        assertThat(RollingUpgrade.lossRate(100, DataClassCodec)).isZero()
    }

    @Test
    fun `with the preserving codec nothing is lost at any rollout percentage`() {
        for (p in listOf(1, 10, 50, 90, 100)) {
            assertThat(RollingUpgrade.lossRate(p, PreservingCodec)).describedAs("v2 at $p%").isZero()
        }
    }

    @Test
    fun `the simulation repeats exactly for the same seed`() {
        assertThat(RollingUpgrade.lossRate(70, DataClassCodec, seed = 3)).isEqualTo(RollingUpgrade.lossRate(70, DataClassCodec, seed = 3))
    }
}
