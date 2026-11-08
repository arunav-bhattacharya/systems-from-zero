package sfz.cons.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercises 1 to 3, one rule at a time, then whole runs on a network that loses nothing. */
class PaxosTest {
    private fun b(round: Int, proposer: Int) = Ballot(round, proposer)

    @Test
    fun `an acceptor promises the first ballot and any higher one, and rejects lower ones`() {
        val a = Acceptor(0)
        assertThat(a.onPrepare(Prepare(b(1, 0)))).isEqualTo(Promise(b(1, 0), null, null))
        assertThat(a.onPrepare(Prepare(b(2, 1)))).isEqualTo(Promise(b(2, 1), null, null))
        assertThat(a.onPrepare(Prepare(b(1, 1)))).isEqualTo(Reject(b(1, 1), b(2, 1)))
        assertThat(a.promised).isEqualTo(b(2, 1))
    }

    @Test
    fun `a duplicate of the prepare it promised gets the same promise again`() {
        val a = Acceptor(0)
        a.onPrepare(Prepare(b(3, 0)))
        assertThat(a.onPrepare(Prepare(b(3, 0)))).isInstanceOf(Promise::class.java)
    }

    @Test
    fun `an acceptor accepts unless it promised higher, and its promises report what it accepted`() {
        val a = Acceptor(0)
        a.onPrepare(Prepare(b(1, 0)))
        assertThat(a.onAccept(Accept(b(1, 0), "capture"))).isEqualTo(Accepted(b(1, 0), "capture"))
        assertThat(a.acceptedBallot).isEqualTo(b(1, 0))
        assertThat(a.acceptedValue).isEqualTo("capture")
        assertThat(a.onPrepare(Prepare(b(2, 1)))).isEqualTo(Promise(b(2, 1), b(1, 0), "capture"))
        assertThat(a.onAccept(Accept(b(1, 0), "capture"))).describedAs("promised 2.1 since").isEqualTo(Reject(b(1, 0), b(2, 1)))
        assertThat(a.onAccept(Accept(b(5, 0), "void"))).describedAs("higher than any promise").isEqualTo(Accepted(b(5, 0), "void"))
        assertThat(a.promised).isEqualTo(b(5, 0))
    }

    @Test
    fun `the value rule takes the highest-numbered accepted proposal, or your own`() {
        val none = listOf(Promise(b(4, 1), null, null), Promise(b(4, 1), null, null))
        assertThat(chooseValue("void", none)).isEqualTo("void")
        val some = listOf(
            Promise(b(4, 1), b(1, 0), "capture"),
            Promise(b(4, 1), null, null),
            Promise(b(4, 1), b(2, 2), "refund"),
        )
        assertThat(chooseValue("void", some)).isEqualTo("refund")
    }

    @Test
    fun `a proposer sends Accept once, at a majority of promises for its current ballot`() {
        val p = Proposer(1, "void", acceptors = 5)
        val prepare = p.startRound()
        assertThat(p.onPromise(0, Promise(prepare.ballot, null, null))).isNull()
        assertThat(p.onPromise(0, Promise(prepare.ballot, null, null))).describedAs("a duplicate counts once").isNull()
        assertThat(p.onPromise(1, Promise(b(0, 9), null, null))).describedAs("an old ballot").isNull()
        assertThat(p.onPromise(1, Promise(prepare.ballot, b(1, 0), "capture"))).isNull()
        assertThat(p.onPromise(2, Promise(prepare.ballot, null, null))).isEqualTo(Accept(prepare.ballot, "capture"))
        assertThat(p.proposed).isEqualTo("capture")
        assertThat(p.onPromise(3, Promise(prepare.ballot, null, null))).describedAs("phase 2 has started").isNull()
    }

    @Test
    fun `a proposer decides at a majority of accepts for its ballot`() {
        val p = Proposer(0, "capture", acceptors = 3)
        val ballot = p.startRound().ballot
        p.onPromise(0, Promise(ballot, null, null))
        p.onPromise(1, Promise(ballot, null, null))
        assertThat(p.onAccepted(0, Accepted(ballot, "capture"))).isNull()
        assertThat(p.onAccepted(0, Accepted(ballot, "capture"))).isNull()
        assertThat(p.onAccepted(2, Accepted(ballot, "capture"))).isEqualTo("capture")
        assertThat(p.decided).isEqualTo("capture")
    }

    @Test
    fun `on a perfect network one proposer decides in two round trips`() {
        val out = runPaxos(PaxosConfig(seed = 7, values = listOf("capture"), minDelayMs = 5, maxDelayMs = 5))
        assertThat(out.decisions).containsEntry(0, "capture")
        assertThat(out.rounds).isEqualTo(1)
        assertThat(out.phase2Ms).containsExactly(10L)
        assertThat(out.messages).isEqualTo(4L * 5)       // prepare, promise, accept, accepted to and from 5 acceptors
    }

    @Test
    fun `two proposers learn the same value`() {
        for (seed in 1L..200L) {
            val out = runPaxos(PaxosConfig(seed = seed))
            assertThat(out.decisions).describedAs("seed $seed").hasSize(2)
            assertThat(out.decisions.values.toSet()).describedAs("seed $seed").hasSize(1)
            assertThat(out.chosen).describedAs("seed $seed").isEqualTo(out.decisions.values.toSet())
        }
    }
}
