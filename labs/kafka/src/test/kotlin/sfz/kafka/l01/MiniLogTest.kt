package sfz.kafka.l01

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test

/** The in-memory log and its readers. No broker needed: these run in well under a second. */
class MiniLogTest {
    private fun logOf(n: Int): MiniLog = MiniLog().apply { repeat(n) { append("acct-${it % 7}", "payment-$it") } }

    @Test
    fun `offsets start at 0 and go up by one with every append`() {
        val log = MiniLog()
        assertThat(log.endOffset).isEqualTo(0)
        assertThat(log.append("acct-17", "auth 40.00 EUR")).isEqualTo(0)
        assertThat(log.append("acct-42", "auth 12.50 EUR")).isEqualTo(1)
        assertThat(log.append(null, "heartbeat")).isEqualTo(2)
        assertThat(log.endOffset).isEqualTo(3)
    }

    @Test
    fun `a read from offset 50 starts at offset 50 and keeps the order`() {
        val log = logOf(100)
        val slice = log.read(from = 50, max = 10)
        assertThat(slice.map { it.offset }).containsExactly(50L, 51L, 52L, 53L, 54L, 55L, 56L, 57L, 58L, 59L)
        assertThat(slice.first().value).isEqualTo("payment-50")
    }

    @Test
    fun `a read near the end returns only what exists`() {
        val log = logOf(100)
        assertThat(log.read(from = 95, max = 10).map { it.offset }).containsExactly(95L, 96L, 97L, 98L, 99L)
    }

    @Test
    fun `reading removes nothing, so the same read returns the same records`() {
        val log = logOf(20)
        val first = log.read(0, 20)
        val second = log.read(0, 20)
        assertThat(second).isEqualTo(first)
        assertThat(log.endOffset).isEqualTo(20)
    }

    @Test
    fun `a read at the end offset is empty, and a read past it is an error`() {
        val log = logOf(5)
        assertThat(log.read(from = 5, max = 10)).isEmpty()
        assertThatThrownBy { log.read(from = 6, max = 10) }.isInstanceOf(IllegalArgumentException::class.java)
        assertThatThrownBy { log.read(from = -1, max = 10) }.isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `a reader's poll moves its position past what it read`() {
        val log = logOf(10)
        val reader = LogReader(log)
        assertThat(reader.poll(4).map { it.offset }).containsExactly(0L, 1L, 2L, 3L)
        assertThat(reader.position).isEqualTo(4)
        assertThat(reader.poll(100).map { it.offset }).containsExactly(4L, 5L, 6L, 7L, 8L, 9L)
        assertThat(reader.position).isEqualTo(10)
        assertThat(reader.poll(100)).isEmpty()
    }

    @Test
    fun `two readers of one log keep separate positions`() {
        val log = logOf(10)
        val ledger = LogReader(log)
        val fraudCheck = LogReader(log)
        ledger.poll(10)
        assertThat(ledger.position).isEqualTo(10)
        assertThat(fraudCheck.position).isEqualTo(0)
        assertThat(fraudCheck.poll(3).map { it.offset }).containsExactly(0L, 1L, 2L)
    }

    @Test
    fun `a reader that starts late or seeks back replays from that offset`() {
        val log = logOf(10)
        val late = LogReader(log, startAt = 7)
        assertThat(late.poll(10).map { it.offset }).containsExactly(7L, 8L, 9L)

        late.seek(2)
        assertThat(late.position).isEqualTo(2)
        assertThat(late.poll(2).map { it.value }).containsExactly("payment-2", "payment-3")
        assertThatThrownBy { late.seek(11) }.isInstanceOf(IllegalArgumentException::class.java)
    }
}
