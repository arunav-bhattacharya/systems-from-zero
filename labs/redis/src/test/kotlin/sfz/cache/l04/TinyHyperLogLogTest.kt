package sfz.cache.l04

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.data.Percentage
import org.junit.jupiter.api.Test

// a model: no Docker needed
class TinyHyperLogLogTest {

    @Test
    fun `adding the same card twice changes nothing`() {
        val hll = TinyHyperLogLog(12)

        assertThat(hll.add("card:1")).isTrue()
        val before = hll.registers()
        assertThat(hll.add("card:1")).isFalse()

        assertThat(hll.registers()).isEqualTo(before)
        assertThat(hll.estimate()).isEqualTo(1)
    }

    @Test
    fun `one add changes at most one register, and only upwards`() {
        val hll = TinyHyperLogLog(8)
        for (i in 0 until 1_000) {
            val before = hll.registers()
            hll.add("card:$i")
            val after = hll.registers()
            val changed = before.indices.filter { before[it] != after[it] }
            assertThat(changed.size).isLessThanOrEqualTo(1)
            changed.forEach { assertThat(after[it]).isGreaterThan(before[it]) }
        }
    }

    @Test
    fun `the register index comes from the low p bits of the hash`() {
        val hll = TinyHyperLogLog(4)
        val card = "card:42"
        val index = (TinyHyperLogLog.hash64(card) and 0xF).toInt()

        hll.add(card)

        val regs = hll.registers()
        assertThat(regs[index]).isPositive()
        assertThat(regs.indices.filter { it != index }.map { regs[it] }).containsOnly(0)
    }

    @Test
    fun `the rank counts the zero bits before the first 1 above the index bits`() {
        // find a card whose hash, after the 4 index bits, starts with exactly three 0 bits
        val card = (0 until 100_000).map { "card:$it" }.first {
            (TinyHyperLogLog.hash64(it) ushr 4) and 0xF == 0b1000L
        }
        val hll = TinyHyperLogLog(4)

        hll.add(card)

        assertThat(hll.registers().max()).isEqualTo(4.toByte())    // 3 zeros, plus one
    }

    @Test
    fun `small counts come out close`() {
        val hll = TinyHyperLogLog(12)
        for (i in 0 until 1_000) hll.add("card:$i")

        assertThat(hll.estimate()).isCloseTo(1_000, Percentage.withPercentage(5.0))
    }

    @Test
    fun `100,000 distinct cards in 4,096 one-byte registers, within 5 percent`() {
        val hll = TinyHyperLogLog(12)
        for (i in 0 until 100_000) {
            hll.add("card:$i")
            hll.add("card:$i")                           // every card pays twice: duplicates don't count
        }

        assertThat(hll.registers()).hasSize(4_096)
        assertThat(hll.estimate()).isCloseTo(100_000, Percentage.withPercentage(5.0))
    }

    @Test
    fun `merging two counters gives exactly the counter of the union`() {
        val monday = TinyHyperLogLog(12)
        val tuesday = TinyHyperLogLog(12)
        val both = TinyHyperLogLog(12)
        for (i in 0 until 60_000) { monday.add("card:$i"); both.add("card:$i") }
        for (i in 40_000 until 100_000) { tuesday.add("card:$i"); both.add("card:$i") }

        monday.merge(tuesday)

        assertThat(monday.registers()).isEqualTo(both.registers())
        assertThat(monday.estimate()).isCloseTo(100_000, Percentage.withPercentage(5.0))
    }
}
