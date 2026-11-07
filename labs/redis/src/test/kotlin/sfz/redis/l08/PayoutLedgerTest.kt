package sfz.redis.l08

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

// a plain model of the fenced store: no Docker
@Timeout(10, unit = TimeUnit.SECONDS)
class PayoutLedgerTest {

    @Test
    fun `a write with a newer or equal fence is accepted`() {
        val ledger = PayoutLedger()

        assertThat(ledger.write("batch-118", 33, "first part")).isTrue()
        assertThat(ledger.write("batch-118", 33, "first and second part")).isTrue()    // the same holder again
        assertThat(ledger.write("batch-118", 34, "from the next holder")).isTrue()

        assertThat(ledger.read("batch-118")).isEqualTo(PayoutLedger.PayoutFile(34, "from the next holder"))
    }

    @Test
    fun `a write with an older fence is refused and changes nothing`() {
        val ledger = PayoutLedger()
        ledger.write("batch-118", 34, "from holder 34")

        assertThat(ledger.write("batch-118", 33, "from holder 33, after its pause")).isFalse()

        assertThat(ledger.read("batch-118")).isEqualTo(PayoutLedger.PayoutFile(34, "from holder 34"))
    }

    @Test
    fun `each batch is fenced on its own`() {
        val ledger = PayoutLedger()
        ledger.write("batch-118", 34, "118")

        assertThat(ledger.write("batch-119", 2, "119")).isTrue()
        assertThat(ledger.read("batch-119")?.fence).isEqualTo(2L)
    }

    @Test
    fun `when fifty writers race, the largest fence wins whatever the order`() {
        val ledger = PayoutLedger()
        val pool = Executors.newFixedThreadPool(50)
        val start = CountDownLatch(1)

        val writes = (1L..50L).shuffled(java.util.Random(7)).map { fence ->
            CompletableFuture.runAsync({ start.await(); ledger.write("batch-118", fence, "holder $fence") }, pool)
        }
        start.countDown()
        writes.forEach { it.get(5, TimeUnit.SECONDS) }
        pool.shutdown()

        assertThat(ledger.read("batch-118")).isEqualTo(PayoutLedger.PayoutFile(50, "holder 50"))
    }
}
