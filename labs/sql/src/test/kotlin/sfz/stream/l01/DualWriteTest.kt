package sfz.stream.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.util.concurrent.TimeUnit

/**
 * Lesson stream-01, exercise 1, in src/main/kotlin/sfz/stream/l01/DualWrite.kt. The service writes
 * PostgreSQL and then the search index; two clients do it at the same moment.
 */
@Timeout(30, unit = TimeUnit.SECONDS)
class DualWriteTest {

    private val index = SearchIndex()

    @BeforeEach
    fun seed() {
        CdcDb.reset()
        CdcDb.seed.forEach(index::put)   // the index starts as a correct copy
    }

    @Test
    fun `two clients racing leave the database and the index different, and nothing fails`() {
        CdcDb.connect().use { capture ->
            CdcDb.connect().use { refund ->
                DualWrite.race(capture, refund, index, "pay-981")   // returns normally: no exception, no error log
            }
        }
        assertThat(CdcDb.rows().getValue("pay-981").status).describedAs("the database saw CAPTURED, then REFUNDED").isEqualTo("REFUNDED")
        assertThat(index.docs.getValue("pay-981").status).describedAs("the index saw REFUNDED, then CAPTURED").isEqualTo("CAPTURED")
        assertThat(index.docs).isNotEqualTo(CdcDb.rows())
    }

    @Test
    fun `the race is deterministic`() {
        repeat(5) {
            CdcDb.reset()
            CdcDb.seed.forEach(index::put)
            CdcDb.connect().use { a -> CdcDb.connect().use { b -> DualWrite.race(a, b, index, "pay-982") } }
            assertThat(CdcDb.rows().getValue("pay-982").status to index.docs.getValue("pay-982").status)
                .describedAs("run ${it + 1}").isEqualTo("REFUNDED" to "CAPTURED")
        }
    }
}
