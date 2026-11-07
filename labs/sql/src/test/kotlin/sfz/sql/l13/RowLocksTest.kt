package sfz.sql.l13

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.opentest4j.AssertionFailedError
import sfz.sql.support.Session
import sfz.sql.support.Sessions
import sfz.sql.support.exerciseSql
import sfz.sql.support.sessions
import sfz.sql.support.splitStatements

/**
 * Lesson sql-13. Your files are src/main/resources/sfz/sql/l13/claim_job.sql and transfer.sql.
 *
 * Row locks are about one transaction waiting for another, so these tests run several real
 * sessions at once and commit for real. Each test puts the seed back afterwards.
 */
class RowLocksTest {

    // ---------------------------------------------------------------- claim_job.sql

    private val restoreJobs = """
        DELETE FROM jobs WHERE job_id > 8;
        UPDATE jobs SET status = 'queued', locked_by = NULL, locked_at = NULL, attempts = 0
        WHERE job_id IN (2, 3, 5, 7, 8);
    """

    private val claim = exerciseSql(13, "claim_job")

    /** A worker session: its application_name is [name], and it has opened a transaction. */
    private fun Sessions.worker(name: String): Session = session(name).also { it.run("BEGIN") }

    /** The job id a claim returned, or null when it returned no row. */
    private fun claimed(rows: sfz.sql.support.Rows?, who: String): Long? {
        if (rows == null) throw AssertionFailedError("claim_job.sql returned no result set for $who; end it with RETURNING job_id, kind, payload")
        rows.assertColumns("job_id", "kind", "payload")
        if (rows.size > 1) throw AssertionFailedError("$who claimed ${rows.size} jobs; a claim takes one:\n$rows")
        return rows.rows.firstOrNull()?.get(0) as Long?
    }

    private fun Sessions.jobState(): String =
        a.run("SELECT job_id, status, locked_by, attempts FROM jobs ORDER BY job_id").toString()

    @Test
    fun `claim_job claims the oldest due job, marks it running and names the worker`() = sessions(restoreJobs) {
        val w1 = worker("worker-1")
        val rows = w1.run(claim)
        assertThat(claimed(rows, "worker-1")).isEqualTo(2L)
        rows!!.assertRowsInOrder(listOf(2L, "fraud_review", """{"payment_id": 31}"""))
        w1.run("COMMIT")
        a.run("SELECT status, locked_by, attempts, locked_at IS NOT NULL AS stamped FROM jobs WHERE job_id = 2")!!
            .assertRowsInOrder(listOf("running", "worker-1", 1L, true))
    }

    @Test
    fun `three workers claim three different jobs at once, and none of them waits`() = sessions(restoreJobs) {
        val workers = (1..3).map { worker("worker-$it") }
        // each claim must finish without queueing behind the transactions still open before it
        val jobs = workers.map { w -> claimed(w.runWithoutWaiting(claim), w.name) }
        assertThat(jobs).describedAs("the jobs the three workers claimed, in order").containsExactly(2L, 3L, 5L)
        workers.forEach { it.run("COMMIT") }
        a.run("SELECT job_id, locked_by FROM jobs WHERE status = 'running' ORDER BY job_id")!!
            .assertRowsInOrder(listOf(2L, "worker-1"), listOf(3L, "worker-2"), listOf(5L, "worker-3"))
    }

    @Test
    fun `a worker never takes a job that another worker has already claimed`() = sessions(restoreJobs) {
        val w1 = worker("worker-1")
        val w2 = worker("worker-2")
        val first = claimed(w1.run(claim), "worker-1")
        val pending = w2.start(claim)
        pending.awaitDoneOrBlocked()               // worker-2 has either finished or is waiting
        w1.run("COMMIT")                           // worker-1's claim of job 2 becomes visible
        val second = claimed(pending.result(), "worker-2")
        w2.run("COMMIT")
        assertThat(second).describedAs("worker-1 claimed job $first; worker-2 must get a different job.\n${jobState()}")
            .isNotEqualTo(first)
        // a job claimed twice would show two attempts
        a.run("SELECT job_id, attempts FROM jobs WHERE status = 'running' ORDER BY job_id")!!
            .assertRowsInOrder(listOf(2L, 1L), listOf(3L, 1L))
    }

    @Test
    fun `when every due job is taken, the next worker gets no row at once`() = sessions(restoreJobs) {
        val workers = (1..6).map { worker("worker-$it") }
        val jobs = workers.map { w -> claimed(w.runWithoutWaiting(claim), w.name) }
        assertThat(jobs).describedAs("five jobs are queued and due; the sixth worker finds none")
            .containsExactly(2L, 3L, 5L, 7L, 8L, null)
        workers.forEach { it.run("COMMIT") }
    }

    @Test
    fun `a job comes back when its worker's transaction rolls back`() = sessions(restoreJobs) {
        val w1 = worker("worker-1")
        assertThat(claimed(w1.run(claim), "worker-1")).isEqualTo(2L)
        w1.run("ROLLBACK")                         // the worker crashed: its connection's transaction ends
        val w2 = worker("worker-2")
        assertThat(claimed(w2.runWithoutWaiting(claim), "worker-2")).describedAs("job 2 is queued again").isEqualTo(2L)
        w2.run("COMMIT")
        a.run("SELECT locked_by, attempts FROM jobs WHERE job_id = 2")!!.assertRowsInOrder(listOf("worker-2", 1L))
    }

    @Test
    fun `claim_job skips jobs that are not queued or not yet due, and takes the oldest first`() = sessions(restoreJobs) {
        a.run(
            """
            INSERT INTO jobs (job_id, kind, payload, status, run_after) VALUES
                (9,  'send_receipt',    '{"payment_id": 2}',  'queued', '2026-01-05 08:31+00'),
                (10, 'send_receipt',    '{"payment_id": 37}', 'queued', now() + interval '1 day'),
                (11, 'settle_merchant', '{"merchant_id": 7}', 'failed', '2026-01-01 00:00+00'),
                (12, 'fraud_review',    '{"payment_id": 15}', 'done',   '2026-01-02 00:00+00')
            """,
        )
        val workers = (1..3).map { worker("worker-$it") }
        val jobs = workers.map { w -> claimed(w.runWithoutWaiting(claim), w.name) }
        assertThat(jobs).describedAs("job 9 is the oldest due job; 10 is not due, 11 failed, 12 is done")
            .containsExactly(9L, 2L, 3L)
        workers.forEach { it.run("COMMIT") }
        a.run("SELECT job_id, status, attempts FROM jobs WHERE job_id IN (10, 11, 12) ORDER BY job_id")!!
            .assertRowsInOrder(listOf(10L, "queued", 0L), listOf(11L, "failed", 0L), listOf(12L, "done", 0L))
    }

    // ---------------------------------------------------------------- transfer.sql

    private val restoreAccounts = """
        DELETE FROM accounts WHERE account_id IN (409, 410);
        UPDATE accounts a
        SET balance_minor = coalesce((SELECT sum(e.amount_minor) FROM ledger_entries e WHERE e.account_id = a.account_id), 0)
        WHERE a.customer_id IN (2, 9, 10);
    """

    private fun transferScript() = splitStatements(exerciseSql(13, "transfer"))

    /** Gives [session] its own one-row transfer table, which transfer.sql reads. */
    private fun transfer(session: Session, from: Long, to: Long, amount: Long) {
        session.run("CREATE TEMP TABLE transfer (from_account bigint NOT NULL, to_account bigint NOT NULL, amount_minor bigint NOT NULL)")
        session.run("INSERT INTO transfer VALUES ($from, $to, $amount)")
    }

    private fun Sessions.balances(vararg ids: Long): List<Long> = ids.map { id ->
        a.run("SELECT balance_minor FROM accounts WHERE account_id = $id")!!.rows.single()[0] as Long
    }

    private fun List<String>.deadlocks() = filter { "40P01" in it }

    @Test
    fun `transfer moves the money from one account to the other`() = sessions(restoreAccounts) {
        transfer(a, 109, 209, 1000)
        val log = interleave(transferScript(), emptyList())
        assertThat(balances(109, 209)).describedAs(log.joinToString("\n")).containsExactly(4000L, 6000L)
    }

    @Test
    fun `two transfers in opposite directions both apply, without a deadlock`() = sessions(restoreAccounts) {
        transfer(a, 109, 209, 1000)                // A: 109 -> 209
        transfer(b, 209, 109, 3000)                // B: 209 -> 109, at the same moment
        val log = interleave(transferScript(), transferScript())
        assertThat(balances(109, 209)).describedAs("both transfers applied once:\n" + log.joinToString("\n"))
            .containsExactly(7000L, 3000L)
        assertThat(log.deadlocks())
            .describedAs("PostgreSQL had to break a deadlock (the retry made the balances right, a second late):\n" + log.joinToString("\n"))
            .isEmpty()
    }

    @Test
    fun `the same holds for two new accounts whose ids run the other way`() = sessions(restoreAccounts) {
        a.run(
            """
            INSERT INTO accounts (account_id, kind, customer_id, balance_minor, opened_at) VALUES
                (409, 'customer', 9,  2000, '2026-07-01 00:00+00'),
                (410, 'customer', 10, 8000, '2026-07-01 00:00+00')
            """,
        )
        transfer(a, 410, 409, 500)                 // A starts from the higher id this time
        transfer(b, 409, 410, 1500)
        val log = interleave(transferScript(), transferScript())
        assertThat(balances(409, 410)).describedAs("both transfers applied once:\n" + log.joinToString("\n"))
            .containsExactly(1000L, 9000L)
        assertThat(log.deadlocks()).describedAs("a deadlock happened:\n" + log.joinToString("\n")).isEmpty()
    }

    @Test
    fun `transfers between different accounts do not wait for each other`() = sessions(restoreAccounts) {
        val ben = balances(102, 202)
        transfer(a, 109, 209, 1000)                // Ivy's accounts
        transfer(b, 102, 202, 2500)                // Ben's accounts
        val log = interleave(transferScript(), transferScript())
        assertThat(log.filter { "waits for a lock" in it })
            .describedAs("lock only the two accounts of the transfer:\n" + log.joinToString("\n"))
            .isEmpty()
        assertThat(balances(109, 209, 102, 202)).containsExactly(4000L, 6000L, ben[0] - 2500, ben[1] + 2500)
    }
}
