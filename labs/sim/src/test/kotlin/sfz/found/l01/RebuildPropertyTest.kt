package sfz.found.l01

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import org.assertj.core.api.Assertions.assertThat
import java.nio.file.Files

/**
 * A property test: jqwik runs it with many random seeds and sizes, and reports the smallest case
 * that breaks it. The property is the definition of derived data: whatever the history, views
 * rebuilt from the log equal the views that were kept up to date live.
 */
class RebuildPropertyTest {
    @Property(tries = 40)
    fun `for any history, rebuilt views equal live views`(@ForAll seed: Long, @ForAll @IntRange(min = 1, max = 200) payments: Int) {
        val file = Files.createTempFile("payments", ".log")
        try {
            val log = PaymentLog(file.also { Files.delete(it) })
            val liveIndex = PaymentIndex()
            val liveTotals = DailyTotals()
            val service = PaymentService(log, listOf(liveIndex, liveTotals))
            val events = Payments.events(seed, payments)
            events.forEach { service.record(it) }

            val index = PaymentIndex()
            val totals = DailyTotals()
            rebuild(log, index, totals)

            for (id in events.map { it.paymentId }) assertThat(index.get(id)).isEqualTo(liveIndex.get(id))
            for (m in Payments.merchants) for (d in Payments.days) assertThat(totals.total(m, d)).isEqualTo(liveTotals.total(m, d))
        } finally {
            Files.deleteIfExists(file)
        }
    }
}
