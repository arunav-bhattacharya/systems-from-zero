package sfz.dist.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Exercises 1 and 2 on the simulated network: 1,000 payments, one every 10 ms. The issuer takes
 * 50 ms per charge; every packet takes 1 ms unless the test adds faults. The client sees only
 * [PaymentClient.outcomes]; the issuer's [PaymentServer.charges] is the truth.
 */
class PartialFailureTest {

    @Test
    fun `on a network that never fails, every payment is approved once`() {
        val run = payments()
        assertThat(run.audit).isEqualTo(Audit(1_000, 1_000, 0, 0, 0, 0))
        assertThat(run.client.outcomes.values).allSatisfy { assertThat(it.attempts).isEqualTo(1) }
        // 1 ms there, 50 ms of work, 1 ms back
        assertThat(run.client.outcomes.getValue("pay-1")).isEqualTo(Outcome.Approved("A00001", 1, 52))
    }

    @Test
    fun `a dead issuer and a paused issuer look the same to the client`() {
        val dead = payments(count = 1, timeoutMs = 1_000, maxAttempts = 3) { it.server.crash() }
        val paused = payments(count = 1, timeoutMs = 1_000, maxAttempts = 3) { it.server.pauseUntil(5_000) }

        // the client's whole view: three attempts, three timeouts, the same decision at the same moment
        assertThat(dead.client.outcomes).isEqualTo(paused.client.outcomes)
        assertThat(dead.client.outcomes.getValue("pay-1")).isEqualTo(Outcome.Unknown(attempts = 3, atMs = 3_000))

        // the truth differs: the paused issuer woke at 5,000 ms and charged the card once
        assertThat(dead.server.charges).isEmpty()
        assertThat(paused.server.charges.map { it.key to it.atMs }).containsExactly("pay-1" to 5_050L)
        assertThat(paused.client.lateReplies).isEqualTo(1)
    }

    @Test
    fun `lost replies and lost requests give the client the same answer and opposite truths`() {
        val repliesLost = payments(replies = Faults(loss = 0.3))
        val requestsLost = payments(requests = Faults(loss = 0.3))

        // about 30% unknown either way
        assertThat(repliesLost.audit.unknown).isBetween(250, 350)
        assertThat(requestsLost.audit.unknown).isBetween(250, 350)
        // every request reached the issuer: every unknown payment was charged
        assertThat(repliesLost.audit.unknownButCharged).isEqualTo(repliesLost.audit.unknown)
        // no lost request was charged
        assertThat(requestsLost.audit.unknownButCharged).isZero()
    }

    @Test
    fun `retries without an idempotency key charge some cards twice`() {
        val run = payments(faults = Faults(loss = 0.2), maxAttempts = 3, dedupe = false)
        assertThat(run.audit.doubleCharged).isGreaterThan(50)
        assertThat(run.audit.extraCharges).isGreaterThanOrEqualTo(run.audit.doubleCharged)
        // retries do cut the unknowns: about 0.36^3 of payments, against 36% with one attempt
        assertThat(run.audit.unknown).isLessThan(100)
    }

    @Test
    fun `an idempotency key makes the same retries safe`() {
        val run = payments(faults = Faults(loss = 0.2), maxAttempts = 3, dedupe = true)
        assertThat(run.audit.doubleCharged).isZero()
        assertThat(run.audit.extraCharges).isZero()
        // every approval carries the code of the one charge for that key
        val codeOf = run.server.charges.associate { it.key to it.code }
        for ((key, outcome) in run.client.outcomes) {
            if (outcome is Outcome.Approved) assertThat(outcome.code).isEqualTo(codeOf[key])
        }
        assertThat(run.client.outcomes.values.filterIsInstance<Outcome.Approved>().count { it.attempts > 1 }).isGreaterThan(100)
    }

    @Test
    fun `a network that duplicates packets charges twice unless the issuer checks the key`() {
        val unchecked = payments(faults = Faults(duplicate = 0.2), dedupe = false)
        val checked = payments(faults = Faults(duplicate = 0.2), dedupe = true)
        assertThat(unchecked.audit.extraCharges).isBetween(150, 250)
        assertThat(checked.audit.extraCharges).isZero()
        assertThat(checked.audit.approved).isEqualTo(1_000)
    }

    @Test
    fun `a reply that arrives after the timeout is a payment that happened`() {
        // nothing is lost, but 10% of packets wait in a queue for up to 3 seconds
        val run = payments(faults = Faults(queueing = 0.1, queueMs = 3_000), timeoutMs = 1_000)
        assertThat(run.audit.unknown).isGreaterThan(50)
        assertThat(run.audit.unknownButCharged).isEqualTo(run.audit.unknown)
        assertThat(run.client.lateReplies).isEqualTo(run.audit.unknown)
    }

    @Test
    fun `retrying a slow request during a pause still charges once with the key`() {
        val unchecked = payments(count = 1, timeoutMs = 1_000, maxAttempts = 3, dedupe = false) { it.server.pauseUntil(5_000) }
        val checked = payments(count = 1, timeoutMs = 1_000, maxAttempts = 3, dedupe = true) { it.server.pauseUntil(5_000) }
        assertThat(unchecked.server.charges).hasSize(3)          // all three attempts waited in the buffer
        assertThat(checked.server.charges).hasSize(1)
    }
}
