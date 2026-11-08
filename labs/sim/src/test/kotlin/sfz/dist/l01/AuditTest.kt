package sfz.dist.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercise 3, [audit], on outcomes and charges written out by hand. */
class AuditTest {
    @Test
    fun `audit counts beliefs against charges`() {
        val outcomes = linkedMapOf(
            "pay-1" to Outcome.Approved("A00001", attempts = 1, atMs = 52),
            "pay-2" to Outcome.Unknown(attempts = 1, atMs = 1_000),      // charged: the reply was lost
            "pay-3" to Outcome.Unknown(attempts = 1, atMs = 1_000),      // never charged: the request was lost
            "pay-4" to Outcome.Approved("A00003", attempts = 2, atMs = 1_052),
        )
        val charges = listOf(
            Charge("pay-1", 1_250, "A00001", 51),
            Charge("pay-2", 1_250, "A00002", 61),
            Charge("pay-4", 1_250, "A00003", 71),
            Charge("pay-4", 1_250, "A00004", 1_051),                    // the retry charged the card again
            Charge("pay-4", 1_250, "A00005", 1_061),
        )
        assertThat(audit(outcomes, charges)).isEqualTo(
            Audit(payments = 4, approved = 2, unknown = 2, unknownButCharged = 1, doubleCharged = 1, extraCharges = 2)
        )
    }

    @Test
    fun `an empty run audits to zeros`() {
        assertThat(audit(emptyMap(), emptyList())).isEqualTo(Audit(0, 0, 0, 0, 0, 0))
    }
}
