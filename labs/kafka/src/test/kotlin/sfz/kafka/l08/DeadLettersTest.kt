package sfz.kafka.l08

import org.apache.kafka.clients.consumer.ConsumerRecord
import org.apache.kafka.common.header.internals.RecordHeaders
import org.apache.kafka.common.record.TimestampType
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.util.Optional

/** The dead-letter record: a faithful copy of the original, plus where it came from and why it failed. */
class DeadLettersTest {
    private val failed = ConsumerRecord(
        "payments", 2, 41L, 0L, TimestampType.CREATE_TIME, 0, 0, "acct-7", "pay-0042,acct-7,12x50",
        RecordHeaders().add("trace-id", "abc123".toByteArray()), Optional.empty(),
    )

    @Test
    fun `the dead-letter topic of payments is payments DLT`() {
        assertThat(DeadLetters.topicFor("payments")).isEqualTo("payments.DLT")
    }

    @Test
    fun `a dead letter keeps the key and value and leaves the partition to the key`() {
        val dl = DeadLetters.deadLetter(failed, NumberFormatException("For input string: \"12x50\""), "payments.DLT")
        assertThat(dl.topic()).isEqualTo("payments.DLT")
        assertThat(dl.partition() as Int?).isNull() // no partition: the producer picks it from the key
        assertThat(dl.key()).isEqualTo("acct-7")
        assertThat(dl.value()).isEqualTo("pay-0042,acct-7,12x50")
    }

    @Test
    fun `its headers say where the record came from and why it failed`() {
        val dl = DeadLetters.deadLetter(failed, NumberFormatException("For input string: \"12x50\""), "payments.DLT")
        val h = dl.headers()
        assertThat(DeadLetters.header(h, DeadLetters.ORIGINAL_TOPIC)).isEqualTo("payments")
        assertThat(DeadLetters.header(h, DeadLetters.ORIGINAL_PARTITION)).isEqualTo("2")
        assertThat(DeadLetters.header(h, DeadLetters.ORIGINAL_OFFSET)).isEqualTo("41")
        assertThat(DeadLetters.header(h, DeadLetters.EXCEPTION_CLASS)).isEqualTo("java.lang.NumberFormatException")
        assertThat(DeadLetters.header(h, DeadLetters.EXCEPTION_MESSAGE)).isEqualTo("For input string: \"12x50\"")
        assertThat(DeadLetters.header(h, "trace-id")).isEqualTo("abc123") // the producer's own headers survive
    }

    @Test
    fun `an exception without a message gives an empty message header`() {
        val dl = DeadLetters.deadLetter(failed, IllegalStateException(), "payments.DLT")
        assertThat(DeadLetters.header(dl.headers(), DeadLetters.EXCEPTION_MESSAGE)).isEmpty()
    }
}
