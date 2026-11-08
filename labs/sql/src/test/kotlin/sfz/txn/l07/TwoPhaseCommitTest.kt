package sfz.txn.l07

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.assertThrows
import org.junit.jupiter.api.io.TempDir
import org.opentest4j.AssertionFailedError
import sfz.sql.support.Rows
import sfz.sql.support.exerciseSql
import sfz.sql.support.row
import java.nio.file.Path
import java.sql.Connection
import java.sql.SQLException
import java.util.concurrent.Executors
import java.util.concurrent.Future
import java.util.concurrent.TimeUnit

/**
 * Lesson txn-07. Your files are src/main/kotlin/sfz/txn/l07/TwoPhaseCommit.kt (exercise 1) and
 * src/main/resources/sfz/txn/l07/in_doubt.sql (exercise 2).
 *
 * A transfer moves 30.00 from wallet w-17 (database `wallets`) to the merchant m-cafe (database
 * `payouts`). The tests run it through your coordinator, make the coordinator "crash" at chosen
 * points, close its connections as a dead process would, and then look at what the two databases
 * hold: what is committed, what is still prepared, and who is stuck waiting.
 */
@Timeout(30, unit = TimeUnit.SECONDS)
class TwoPhaseCommitTest {

    @TempDir
    lateinit var dir: Path

    private val opened = mutableListOf<Connection>()
    private val log by lazy { DecisionLog(dir.resolve("coordinator.log")) }

    @BeforeEach
    fun seed() = TwoPcDb.reset()

    @AfterEach
    fun cleanUp() {
        opened.forEach { runCatching { it.close() } }
        TwoPcDb.reset()
    }

    private fun connect(db: String): Connection = TwoPcDb.connect(db).also { opened += it }

    /** A coordinator process: fresh connections to both databases, and the shared log on disk. */
    private fun coordinator(crashAt: CrashPoint = CrashPoint.NONE): Pair<Coordinator, List<Connection>> {
        val conns = listOf(connect("wallets"), connect("payouts"))
        val ps = listOf(Participant("wallets", conns[0]), Participant("payouts", conns[1]))
        return Coordinator(ps, log, crashAt) to conns
    }

    /** Runs the transfer in a coordinator that dies at [point], then closes its connections, as the kernel would. */
    private fun crashDuringTransfer(point: CrashPoint, txId: String = "txf-1") {
        val (c, conns) = coordinator(point)
        val crash = assertThrows<CoordinatorCrashed>("the coordinator should have crashed at $point") { c.run(txId, transfer(txId)) }
        assertThat(crash.point).isEqualTo(point)
        conns.forEach { it.close() }
    }

    private fun transfer(txId: String, amount: Long = 3000) = mapOf(
        "wallets" to listOf("UPDATE wallets SET balance_minor = balance_minor - $amount WHERE id = 'w-17'"),
        "payouts" to listOf(
            "UPDATE merchant_balances SET balance_minor = balance_minor + $amount WHERE id = 'm-cafe'",
            "INSERT INTO payout_entries (transfer_id, merchant_id, amount_minor) VALUES ('$txId', 'm-cafe', $amount)",
        ),
    )

    private fun wallet() = TwoPcDb.long("wallets", "SELECT balance_minor FROM wallets WHERE id = 'w-17'")
    private fun merchant() = TwoPcDb.long("payouts", "SELECT balance_minor FROM merchant_balances WHERE id = 'm-cafe'")

    // ---------------------------------------------------------------- exercise 1: run

    @Test
    fun `a transfer commits on both databases and leaves nothing prepared`() {
        val (c, _) = coordinator()
        assertThat(c.run("txf-1", transfer("txf-1"))).isEqualTo(Outcome.Committed)
        assertThat(wallet()).describedAs("w-17 after the transfer").isEqualTo(7000)
        assertThat(merchant()).describedAs("m-cafe after the transfer").isEqualTo(3000)
        assertThat(TwoPcDb.preparedGids()).describedAs("transactions still prepared").isEmpty()
        assertThat(log.committed("txf-1")).describedAs("the log records the commit decision").isTrue()
    }

    @Test
    fun `a participant that votes no aborts the transfer, and the one that already prepared is rolled back`() {
        // payouts already holds an entry for txf-dup, so its INSERT fails with a unique violation
        val (c, _) = coordinator()
        val outcome = c.run("txf-dup", transfer("txf-dup"))
        assertThat(outcome).isEqualTo(Outcome.Aborted("payouts", "23505"))
        assertThat(wallet()).describedAs("w-17 was prepared first, so it must have been rolled back").isEqualTo(10000)
        assertThat(merchant()).isEqualTo(0)
        assertThat(TwoPcDb.preparedGids()).describedAs("nothing may stay prepared after an abort").isEmpty()
        assertThat(log.committed("txf-dup")).describedAs("an abort writes no commit decision").isFalse()
    }

    @Test
    fun `a failure on the first participant aborts before the second one is touched`() {
        // 200.00 out of a wallet holding 100.00 breaks the CHECK (balance_minor >= 0)
        val (c, _) = coordinator()
        assertThat(c.run("txf-2", transfer("txf-2", amount = 20000))).isEqualTo(Outcome.Aborted("wallets", "23514"))
        assertThat(wallet()).isEqualTo(10000)
        assertThat(merchant()).describedAs("payouts must not run its part once wallets voted no").isEqualTo(0)
        assertThat(TwoPcDb.preparedGids()).isEmpty()
    }

    @Test
    fun `after a crash between prepare and decision both databases are in doubt and hold their row locks`() {
        crashDuringTransfer(CrashPoint.AFTER_PREPARE)
        assertThat(TwoPcDb.preparedGids()).describedAs("prepared transactions survive their coordinator")
            .containsExactly("txf-1@payouts", "txf-1@wallets")
        assertThat(log.committed("txf-1")).isFalse()
        // readers see the old committed versions: nothing is visible until COMMIT PREPARED
        assertThat(wallet()).isEqualTo(10000)
        assertThat(merchant()).isEqualTo(0)
        // a writer on w-17 waits for the in-doubt transaction's row lock
        val other = connect("wallets")
        other.createStatement().use { it.execute("SET lock_timeout = '300ms'") }
        val e = assertThrows<SQLException> {
            other.createStatement().use { it.execute("UPDATE wallets SET balance_minor = balance_minor - 100 WHERE id = 'w-17'") }
        }
        assertThat(e.sqlState).describedAs("lock_timeout fired: the row is still locked").isEqualTo("55P03")
    }

    // ---------------------------------------------------------------- exercise 1: recover

    @Test
    fun `recovery rolls back what the log never decided`() {
        crashDuringTransfer(CrashPoint.AFTER_PREPARE)
        val (c, _) = coordinator()
        assertThat(c.recover()).isEqualTo(RecoveryReport(committed = emptyList(), rolledBack = listOf("txf-1@wallets", "txf-1@payouts")))
        assertThat(TwoPcDb.preparedGids()).isEmpty()
        assertThat(wallet()).isEqualTo(10000)
        assertThat(merchant()).isEqualTo(0)
    }

    @Test
    fun `recovery commits what the log decided when the coordinator died before telling anyone`() {
        crashDuringTransfer(CrashPoint.AFTER_DECISION)
        assertThat(log.committed("txf-1")).describedAs("the decision was on disk before the crash").isTrue()
        assertThat(wallet()).describedAs("decided but not yet committed anywhere").isEqualTo(10000)
        val (c, _) = coordinator()
        assertThat(c.recover()).isEqualTo(RecoveryReport(committed = listOf("txf-1@wallets", "txf-1@payouts"), rolledBack = emptyList()))
        assertThat(wallet()).isEqualTo(7000)
        assertThat(merchant()).isEqualTo(3000)
        assertThat(TwoPcDb.preparedGids()).isEmpty()
    }

    @Test
    fun `a crash between the two commits shows half a transfer until recovery finishes it`() {
        crashDuringTransfer(CrashPoint.AFTER_FIRST_COMMIT)
        assertThat(wallet()).describedAs("wallets already committed").isEqualTo(7000)
        assertThat(merchant()).describedAs("payouts is still in doubt").isEqualTo(0)
        assertThat(TwoPcDb.preparedGids()).containsExactly("txf-1@payouts")
        val (c, _) = coordinator()
        assertThat(c.recover()).isEqualTo(RecoveryReport(committed = listOf("txf-1@payouts"), rolledBack = emptyList()))
        assertThat(merchant()).isEqualTo(3000)
    }

    @Test
    fun `recovery leaves other coordinators' transactions alone and finds nothing the second time`() {
        // another coordinator's branch on wallets, in doubt too
        connect("wallets").createStatement().use {
            it.execute("BEGIN")
            it.execute("UPDATE wallets SET balance_minor = balance_minor + 1 WHERE id = 'w-18'")
            it.execute("PREPARE TRANSACTION 'batch-9@ledger'")
        }
        crashDuringTransfer(CrashPoint.AFTER_DECISION)
        val (c, _) = coordinator()
        assertThat(c.recover()).isEqualTo(RecoveryReport(committed = listOf("txf-1@wallets", "txf-1@payouts"), rolledBack = emptyList()))
        assertThat(TwoPcDb.preparedGids()).describedAs("someone else's in-doubt transaction is not ours to decide")
            .containsExactly("batch-9@ledger")
        assertThat(c.recover()).describedAs("a second recovery right after the first")
            .isEqualTo(RecoveryReport(emptyList(), emptyList()))
    }

    // ---------------------------------------------------------------- exercise 2: in_doubt.sql

    private val inDoubt = exerciseSql("txn/l07", "in_doubt")

    private fun query(db: String, sql: String): Rows = connect(db).createStatement().use { st ->
        try {
            st.executeQuery(sql).use { Rows.from(it) }
        } catch (e: SQLException) {
            throw AssertionFailedError("in_doubt.sql failed on $db with SQLSTATE ${e.sqlState}: ${e.message}", e)
        }
    }

    @Test
    fun `in_doubt counts the sessions waiting for each in-doubt transaction in this database`() {
        crashDuringTransfer(CrashPoint.AFTER_PREPARE)
        val pool = Executors.newSingleThreadExecutor()
        try {
            val waiter = connect("wallets")
            waiter.createStatement().use { it.execute("SET lock_timeout = '10s'") }
            val pending: Future<*> = pool.submit {
                runCatching { waiter.createStatement().use { it.execute("UPDATE wallets SET balance_minor = 0 WHERE id = 'w-17'") } }
            }
            awaitLockWait()
            query("wallets", inDoubt).run {
                assertColumns("gid", "waiting")
                assertRowsInOrder(row("txf-1@wallets", 1))
            }
            query("payouts", inDoubt).assertRowsInOrder(row("txf-1@payouts", 0))
            TwoPcDb.reset() // cancels the waiter and rolls the in-doubt transactions back
            pending.get(5, TimeUnit.SECONDS)
        } finally {
            pool.shutdownNow()
        }
    }

    @Test
    fun `in_doubt shows only this database's in-doubt transactions, even when nobody waits for them`() {
        // another coordinator's transaction, prepared on payouts only
        connect("payouts").createStatement().use {
            it.execute("BEGIN")
            it.execute("UPDATE merchant_balances SET balance_minor = balance_minor + 1 WHERE id = 'm-cafe'")
            it.execute("PREPARE TRANSACTION 'batch-3@ledger'")
        }
        query("wallets", inDoubt).run {
            assertColumns("gid", "waiting")
            assertRowsInOrder() // nothing is prepared in wallets
        }
        query("payouts", inDoubt).assertRowsInOrder(row("batch-3@ledger", 0))
    }

    /** Waits until some session on the server is waiting for a lock. */
    private fun awaitLockWait() {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
        while (System.nanoTime() < deadline) {
            if (TwoPcDb.long("sfz", "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock'") > 0) return
            Thread.sleep(10)
        }
        throw AssertionFailedError("the second writer never started waiting for the in-doubt row lock")
    }
}
