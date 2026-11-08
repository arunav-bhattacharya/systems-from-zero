package sfz.derive.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** The pieces one at a time: the derivation function, the feed, the client copy and the waiting read. */
class DataflowTest {
    @Test
    fun `apply turns one transfer into two diffs, payer first`() {
        val view = Balances(mapOf("acc-01" to 10_000L, "acc-02" to 500L))
        val diffs = view.apply(Entry(7, Transfer("tr-1", "acc-01", "acc-02", 4_500)))

        assertThat(diffs).containsExactly(Diff(7, "acc-01", -4_500), Diff(7, "acc-02", 4_500))
        assertThat(view.get("acc-01")).isEqualTo(5_500)
        assertThat(view.get("acc-02")).isEqualTo(5_000)
    }

    @Test
    fun `since returns one account's diffs after an offset, in order`() {
        val feed = Feed(Sim())
        feed.publish(listOf(Diff(0, "acc-01", -100), Diff(0, "acc-02", 100)))
        feed.publish(listOf(Diff(1, "acc-02", -50), Diff(1, "acc-01", 50)))
        feed.publish(listOf(Diff(2, "acc-01", -7), Diff(2, "acc-03", 7)))

        assertThat(feed.since("acc-01", 0)).containsExactly(Diff(1, "acc-01", 50), Diff(2, "acc-01", -7))
        assertThat(feed.since("acc-01", -1)).hasSize(3)
        assertThat(feed.since("acc-01", 2)).isEmpty()
    }

    @Test
    fun `a client copy applies each newer diff once and ignores repeats and old ones`() {
        val copy = ClientCopy("acc-01", startBalance = 1_000, startOffset = 4)

        copy.receive(Diff(3, "acc-01", -200))                     // the snapshot already had it
        copy.receive(Diff(6, "acc-01", -300))
        copy.receive(Diff(6, "acc-01", -300))                     // pushed twice
        copy.receive(Diff(9, "acc-01", 50))
        copy.receive(Diff(8, "acc-01", -1))                       // late and older than 9

        assertThat(copy.balance).isEqualTo(750)
        assertThat(copy.lastOffset).isEqualTo(9)
        assertThat(copy.applied).isEqualTo(2)
        assertThat(copy.ignored).isEqualTo(3)
    }

    @Test
    fun `a read for an offset the view already has is answered at once`() {
        val app = App(seed = 1)
        val offset = app.transfer(Transfer("tr-1", "acc-01", "acc-02", 1_000))
        app.sim.runUntil(50)                                      // the first poll applies it
        assertThat(app.processor.applied).isEqualTo(offset)

        var answer: Read? = null
        app.processor.readAfter("acc-01", offset) { answer = it }

        assertThat(answer).isEqualTo(Read("acc-01", OPENING_CENTS - 1_000, offset))
        assertThat(app.processor.waiting).isZero()
    }

    @Test
    fun `a parked read is answered by the poll that applies its offset, and only once`() {
        val app = App(seed = 1)
        val offset = app.transfer(Transfer("tr-1", "acc-01", "acc-02", 1_000))
        val answers = ArrayList<Pair<Long, Read>>()
        app.processor.readAfter("acc-01", offset) { answers += app.sim.now to it }

        assertThat(answers).isEmpty()                             // the view is behind: parked
        assertThat(app.processor.waiting).isEqualTo(1)

        app.sim.runUntil(1_000)                                   // many polls

        assertThat(answers).containsExactly(50L to Read("acc-01", OPENING_CENTS - 1_000, offset))
        assertThat(app.processor.waiting).isZero()
    }

    @Test
    fun `a read waiting for a later offset stays parked when an earlier one is applied`() {
        val app = App(seed = 1)
        app.transfer(Transfer("tr-1", "acc-01", "acc-02", 1_000))
        app.sim.runUntil(50)
        val second = app.transfer(Transfer("tr-2", "acc-01", "acc-03", 2_000))
        var answer: Read? = null
        app.processor.readAfter("acc-01", second) { answer = it }
        app.processor.poll()                                      // applies tr-2: now it can answer

        assertThat(answer).isEqualTo(Read("acc-01", OPENING_CENTS - 3_000, second))
    }
}
