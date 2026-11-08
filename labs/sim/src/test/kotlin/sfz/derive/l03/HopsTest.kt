package sfz.derive.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Each hop's own duplicate suppression, and the edge where it stops. */
class HopsTest {
    private val req = Request("req-000001", "acc-01", "acc-02", 4_500)

    @Test
    fun `a connection delivers a request once even if the network repeats it`() {
        val c = Connection(0)
        assertThat(c.receive(0, req)).isEqualTo(req)
        assertThat(c.receive(0, req)).isNull()                     // the retransmitted copy
        assertThat(c.receive(1, req.copy(requestId = "req-000002"))).isNotNull()
    }

    @Test
    fun `a new connection knows nothing about the requests of the old one`() {
        Connection(0).receive(0, req)
        assertThat(Connection(1).receive(0, req)).isEqualTo(req)   // the retry: a new request to TCP
    }

    @Test
    fun `the idempotent broker appends a resent batch once and returns the first offset`() {
        val b = Broker(idempotent = true)
        b.append(1, 0, req.copy(requestId = "req-000000"), "x")
        val first = b.append(1, 1, req, "a")
        val resend = b.append(1, 1, req, "a/resend")

        assertThat(resend).isEqualTo(first)
        assertThat(b.end).isEqualTo(2)
    }

    @Test
    fun `the broker can't tell a new send of the same transfer from a new transfer`() {
        val b = Broker(idempotent = true)
        b.append(1, 0, req, "a")
        b.append(1, 1, req, "b")                                   // the server sent it again: new sequence
        b.append(2, 0, req, "c")                                   // or another producer did
        assertThat(b.end).isEqualTo(3)
    }

    @Test
    fun `without idempotence the broker appends every copy`() {
        val b = Broker(idempotent = false)
        b.append(1, 0, req, "a")
        b.append(1, 0, req, "a/resend")
        assertThat(b.end).isEqualTo(2)
        assertThat(b.get(1).trace).isEqualTo("a/resend")
    }

    @Test
    fun `the ledger posts a request id once, and the repeat moves no money`() {
        val ledger = Ledger(mapOf("acc-01" to 10_000L, "acc-02" to 0L))
        val row = Row("req-000001", "acc-01", "acc-02", 4_500)

        assertThat(ledger.postOnce(row, now = 0)).isTrue()
        assertThat(ledger.postOnce(row, now = 5_000)).isFalse()

        assertThat(ledger.rows).hasSize(1)
        assertThat(ledger.balance("acc-01")).isEqualTo(5_500)
        assertThat(ledger.balance("acc-02")).isEqualTo(4_500)
    }

    @Test
    fun `a retry that arrives after the dedupe window is a new transfer again`() {
        val hour = 3_600_000L
        val row = Row("req-000001", "acc-01", "acc-02", 4_500)

        val short = Ledger(mapOf("acc-01" to 10_000L))
        short.postOnce(row, now = 0)
        short.prune(olderThan = 2 * hour - 1 * hour)               // keep ids for 1 hour
        assertThat(short.postOnce(row, now = 2 * hour)).isTrue()   // the phone was offline for 2 hours
        assertThat(short.rows).hasSize(2)

        val long = Ledger(mapOf("acc-01" to 10_000L))
        long.postOnce(row, now = 0)
        long.prune(olderThan = 2 * hour - 48 * hour)               // keep ids for 48 hours
        assertThat(long.postOnce(row, now = 2 * hour)).isFalse()
        assertThat(long.rows).hasSize(1)
    }

    @Test
    fun `the phone sends the same request id on every attempt`() {
        var n = 0
        val phone = Phone({ "req-%06d".format(++n) })
        val seen = ArrayList<Pair<Int, String>>()
        val flaky = Endpoint { r, _, attempt -> seen += attempt to r.requestId; attempt == 3 }   // two timeouts

        val sent = phone.send(flaky, intent = 0, from = "acc-01", to = "acc-02", cents = 4_500)

        assertThat(sent).containsExactly("req-000001", "req-000001", "req-000001")
        assertThat(seen.map { it.first }).containsExactly(1, 2, 3)
        assertThat(seen.map { it.second }.toSet()).hasSize(1)
    }
}
