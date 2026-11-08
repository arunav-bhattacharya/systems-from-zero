package sfz.derive.l02

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.random.Random

/** The write path extended to the screen: diffs pushed to clients, and a client that resumes. */
class PushTest {
    /** Schedules [n] random transfers over the first minute, with the test's own random numbers. */
    private fun traffic(app: App, seed: Long, n: Int = 1_000) {
        val random = Random(seed)
        repeat(n) { i ->
            val from = ACCOUNTS[random.nextInt(ACCOUNTS.size)]
            val to = ACCOUNTS.filter { it != from }[random.nextInt(ACCOUNTS.size - 1)]
            val t = Transfer("tr-$i", from, to, 100 + random.nextLong(9_900))
            app.sim.at(random.nextLong(60_000)) { app.transfer(t) }
        }
    }

    private fun touches(log: Log, account: String): Int =
        (0 until log.end).count { log.get(it).transfer.let { t -> t.from == account || t.to == account } }

    @Test
    fun `a subscribed client's copy follows the view, applying each change once`() {
        val app = App(seed = 7)
        val subs = ACCOUNTS.take(10).map { Subscription(app.feed, app.snapshot(it)) }
        traffic(app, seed = 7)

        app.sim.runUntil(61_000)

        for (s in subs) {
            val c = s.client
            assertThat(c.balance).describedAs(c.account).isEqualTo(app.view.get(c.account))
            assertThat(c.applied).isEqualTo(touches(app.log, c.account))
            assertThat(c.ignored).isZero()
        }
    }

    @Test
    fun `a client that goes offline catches up from its last offset when it reconnects`() {
        val app = App(seed = 7)
        val sub = Subscription(app.feed, app.snapshot("acc-01"))
        traffic(app, seed = 7)
        var behind = 0L
        app.sim.at(10_000) { sub.drop() }
        app.sim.at(29_999) { behind = app.view.get("acc-01") - sub.client.balance }
        app.sim.at(30_000) { sub.reconnect() }

        app.sim.runUntil(61_000)

        assertThat(behind).isNotZero()                            // offline, the screen was out of date
        assertThat(sub.client.balance).isEqualTo(app.view.get("acc-01"))
        assertThat(sub.client.applied).isEqualTo(touches(app.log, "acc-01"))
    }

    @Test
    fun `a diff that arrives from the catch-up and again live is applied once`() {
        val app = App(seed = 1)
        val sub = Subscription(app.feed, app.snapshot("acc-01"), latencyMs = 20)
        app.transfer(Transfer("tr-1", "acc-01", "acc-02", 1_000))   // applied and pushed at 50 ms, lands at 70 ms
        app.sim.at(55) { sub.drop() }
        app.sim.at(60) { sub.reconnect() }                          // catch-up delivers it at 60 ms

        app.sim.runUntil(200)

        assertThat(sub.client.balance).isEqualTo(OPENING_CENTS - 1_000)
        assertThat(sub.client.applied).isEqualTo(1)
        assertThat(sub.client.ignored).isEqualTo(1)                 // the live copy at 70 ms
    }

    @Property(tries = 25)
    fun `for any seed, waiting reads are never stale and every subscriber converges`(@ForAll seed: Long) {
        val out = ReadYourWrites.run(seed, ReadMode.AFTER_MY_WRITE, transfers = 300)
        assertThat(out.stale).isZero()
        assertThat(out.reads).hasSize(300)

        val app = App(seed)
        val subs = ACCOUNTS.take(5).map { Subscription(app.feed, app.snapshot(it)) }
        traffic(app, seed, n = 300)
        app.sim.at(20_000) { subs[0].drop() }
        app.sim.at(40_000) { subs[0].reconnect() }
        app.sim.runUntil(61_000)
        for (s in subs) assertThat(s.client.balance).isEqualTo(app.view.get(s.client.account))
    }
}
