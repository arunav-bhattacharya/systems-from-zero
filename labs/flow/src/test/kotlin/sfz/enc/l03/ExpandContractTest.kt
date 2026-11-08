package sfz.enc.l03

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.sql.Connection
import java.sql.SQLException
import kotlin.random.Random

/** Moving payouts.amount (euros) to payouts.amount_minor (cents) while the service keeps running. */
class ExpandContractTest {
    private lateinit var conn: Connection
    private val expected = HashMap<Long, Long>() // id -> cents, what the last write meant

    /** Counts what a rollout window saw go wrong. */
    data class Window(var errors: Int = 0, var wrongReads: Int = 0)

    @BeforeEach
    fun setUp() {
        conn = PayoutsDb.connect()
        PayoutsDb.reset(conn)
        for (id in 1L..1000L) expected[id] = id * 7
        PayoutsV3.mismatches.set(0)
    }

    @AfterEach
    fun tearDown() = conn.close()

    /**
     * A rolling deploy from [old] to [new]: [ops] requests, where the share sent to [new] grows from 0% to 100%.
     * Each request writes a payout (sometimes a new id) or reads one and checks it against what was last written.
     */
    private fun rollout(old: PayoutApp, new: PayoutApp, ops: Int = 400, seed: Int = 1): Window {
        val rnd = Random(seed)
        val w = Window()
        for (i in 0 until ops) {
            val app = if (rnd.nextInt(ops) < i) new else old
            val id = rnd.nextLong(1, 1101)
            try {
                if (rnd.nextBoolean()) {
                    val cents = rnd.nextLong(1, 10_000_000)
                    app.save(conn, id, "merchant-${id % 50}", cents)
                    expected[id] = cents
                } else if (app.amountMinorOf(conn, id) != expected[id]) {
                    w.wrongReads++
                }
            } catch (e: SQLException) {
                w.errors++
            }
        }
        return w
    }

    private fun backfillAll(limit: Int): List<Int> =
        generateSequence { Migration.backfillBatch(conn, limit) }.takeWhile { it > 0 }.toList()

    @Test
    fun `renaming in place breaks v1 at once, expanding does not`() {
        conn.createStatement().use { it.execute("ALTER TABLE payouts RENAME COLUMN amount TO amount_minor") }
        assertThatThrownBy { PayoutsV1.save(conn, 1, "m", 4000) }
            .isInstanceOf(SQLException::class.java)
            .satisfies({ assertThat((it as SQLException).sqlState).isEqualTo("42703") }) // undefined_column
        PayoutsDb.reset(conn)

        Migration.expand(conn)
        assertThat(PayoutsDb.columns(conn)).containsEntry("amount_minor", true)
        PayoutsV1.save(conn, 1, "m", 4000)
        assertThat(PayoutsV1.amountMinorOf(conn, 1)).isEqualTo(4000)
    }

    @Test
    fun `v1 and v2 run side by side without errors, and v2 writes both columns`() {
        Migration.expand(conn)
        val w = rollout(PayoutsV1, PayoutsV2)
        assertThat(w).isEqualTo(Window(0, 0))
        PayoutsV2.save(conn, 5000, "m", 4000)
        assertThat(PayoutsDb.count(conn, "SELECT amount_minor FROM payouts WHERE id = 5000")).isEqualTo(4000)
        assertThat(PayoutsDb.count(conn, "SELECT (amount * 100)::bigint FROM payouts WHERE id = 5000")).isEqualTo(4000)
    }

    @Test
    fun `backfill fills every row in batches no larger than the limit`() {
        Migration.expand(conn)
        PayoutsV2.save(conn, 3, "m", 21)            // dual-written and correct: nothing to do
        PayoutsV2.save(conn, 4, "m", 500)           // dual-written...
        PayoutsV1.save(conn, 4, "m", 600)           // ...then changed by v1, which left amount_minor at 500
        val batches = backfillAll(limit = 100)
        assertThat(batches).hasSize(10).allMatch { it <= 100 }
        assertThat(batches.sum()).isEqualTo(999)
        assertThat(PayoutsDb.count(conn, "SELECT count(*) FROM payouts WHERE amount_minor IS NULL")).isZero()
        assertThat(PayoutsDb.count(conn, "SELECT count(*) FROM payouts WHERE amount_minor <> amount * 100")).isZero()
        assertThat(PayoutsDb.count(conn, "SELECT amount_minor FROM payouts WHERE id = 4")).isEqualTo(600)
        assertThat(Migration.backfillBatch(conn, 100)).isZero()
    }

    @Test
    fun `the whole migration runs with zero errors, zero wrong reads and zero mismatches`() {
        Migration.expand(conn)
        assertThat(rollout(PayoutsV1, PayoutsV2, seed = 1)).isEqualTo(Window(0, 0))
        backfillAll(limit = 250)                      // only now: every running instance dual-writes
        assertThat(rollout(PayoutsV2, PayoutsV3, seed = 2)).isEqualTo(Window(0, 0))
        assertThat(PayoutsV3.mismatches.get()).isZero()
        Migration.prepareSwitchWrites(conn)
        assertThat(rollout(PayoutsV3, PayoutsV4, seed = 3)).isEqualTo(Window(0, 0)) // amount goes stale now, unread
        Migration.contract(conn)
        assertThat(PayoutsDb.columns(conn).keys).containsExactly("id", "merchant", "amount_minor")
        assertThat(rollout(PayoutsV4, PayoutsV4, seed = 4)).isEqualTo(Window(0, 0))
        for ((id, cents) in expected) assertThat(PayoutsV4.amountMinorOf(conn, id)).describedAs("payout %d", id).isEqualTo(cents)
    }

    @Test
    fun `a backfill that runs while v1 still writes leaves stale rows, and the shadow read catches them`() {
        Migration.expand(conn)
        backfillAll(limit = 250)                      // too early: v1 instances are still running
        rollout(PayoutsV1, PayoutsV1, ops = 200, seed = 5) // v1 updates amount and leaves amount_minor behind
        val stale = PayoutsDb.count(conn, "SELECT count(*) FROM payouts WHERE amount_minor <> amount * 100")
        assertThat(stale).isPositive()
        val w = rollout(PayoutsV2, PayoutsV3, ops = 400, seed = 6)
        assertThat(w.wrongReads).isPositive()         // v3 serves the stale new column
        assertThat(PayoutsV3.mismatches.get()).isPositive()
    }

    @Test
    fun `contract too early breaks the versions that still read the old column`() {
        Migration.expand(conn)
        backfillAll(limit = 500)
        Migration.contract(conn)                      // v2 and v3 are still running
        assertThatThrownBy { PayoutsV2.save(conn, 1, "m", 4000) }.isInstanceOf(SQLException::class.java)
        assertThatThrownBy { PayoutsV3.amountMinorOf(conn, 1) }.isInstanceOf(SQLException::class.java)
        assertThat(PayoutsV4.amountMinorOf(conn, 1)).isEqualTo(7)
    }
}
