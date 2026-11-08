package sfz.derive.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * The read-your-writes experiment: 1,000 users each transfer money and then read their own
 * balance. The timings come from the seeded simulation, so the counts are exact.
 */
class ReadYourWritesTest {
    /** The balance [account] had after the log entries 0..[upTo], computed straight from the log. */
    private fun fromLog(log: Log, account: String, upTo: Long): Long {
        var b = OPENING_CENTS
        for (o in 0..upTo) {
            val t = log.get(o).transfer
            if (t.from == account) b -= t.cents
            if (t.to == account) b += t.cents
        }
        return b
    }

    @Test
    fun `reading the view right after your own write misses it 331 times in 1,000`() {
        val out = ReadYourWrites.run(seed = 2026, mode = ReadMode.NOW)

        assertThat(out.reads).hasSize(1_000)
        assertThat(out.stale).isEqualTo(331)
        for (r in out.reads) {                                    // stale, but never wrong for its offset
            assertThat(r.read.balance).isEqualTo(fromLog(out.app.log, r.read.account, r.read.appliedOffset))
        }
    }

    @Test
    fun `waiting for your own offset removes every stale read`() {
        val out = ReadYourWrites.run(seed = 2026, mode = ReadMode.AFTER_MY_WRITE)

        assertThat(out.reads).hasSize(1_000)
        assertThat(out.stale).isZero()
        assertThat(out.app.processor.waiting).isZero()
        for (r in out.reads) {
            assertThat(r.read.appliedOffset).isGreaterThanOrEqualTo(r.writeOffset)
            assertThat(r.read.balance).isEqualTo(fromLog(out.app.log, r.read.account, r.read.appliedOffset))
        }
    }

    @Test
    fun `the price is a wait of up to one poll interval, paid by the reads that would have been stale`() {
        val now = ReadYourWrites.run(seed = 2026, mode = ReadMode.NOW)
        val waited = ReadYourWrites.run(seed = 2026, mode = ReadMode.AFTER_MY_WRITE)

        assertThat(waited.reads.count { it.waitMs > 0 }).isEqualTo(now.stale)
        assertThat(waited.waitPercentile(50.0)).isEqualTo(0)
        assertThat(waited.waitPercentile(90.0)).isEqualTo(20)
        assertThat(waited.waitPercentile(99.0)).isEqualTo(37)
        assertThat(waited.reads.maxOf { it.waitMs }).isLessThanOrEqualTo(60)
    }
}
