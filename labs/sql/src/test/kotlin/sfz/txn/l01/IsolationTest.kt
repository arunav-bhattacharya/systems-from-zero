package sfz.txn.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.sql.support.CourseDb
import sfz.sql.support.Session
import sfz.sql.support.Sessions
import sfz.sql.support.exerciseSql
import sfz.sql.support.sessions
import sfz.sql.support.splitStatements
import java.sql.Connection
import java.sql.SQLException
import java.util.concurrent.CyclicBarrier
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * Lesson txn-01. Your files are src/main/resources/sfz/txn/l01/withdraw.sql and
 * src/main/kotlin/sfz/txn/l01/Retry.kt.
 *
 * Isolation is about what one session sees of another's committed work, so these tests commit
 * for real, in two sessions at once. Each one puts the seed back afterwards: every balance it
 * touched is recomputed from the ledger, and any account it added is deleted.
 */
class IsolationTest {

    private val restore = """
        DELETE FROM accounts WHERE account_id = 409;
        UPDATE accounts a
        SET balance_minor = coalesce((SELECT sum(e.amount_minor) FROM ledger_entries e WHERE e.account_id = a.account_id), 0)
        WHERE a.customer_id IN (2, 9);
    """

    private fun withdrawScript() = splitStatements(exerciseSql("txn/l01", "withdraw"))

    /** Gives [session] its own one-row withdrawal table, which withdraw.sql reads. */
    private fun withdrawal(session: Session, accountId: Long, amount: Long) {
        session.run("CREATE TEMP TABLE withdrawal (account_id bigint NOT NULL, amount_minor bigint NOT NULL)")
        session.run("INSERT INTO withdrawal VALUES ($accountId, $amount)")
    }

    private fun Sessions.balances(vararg ids: Long): List<Long> = ids.map { id ->
        a.run("SELECT balance_minor FROM accounts WHERE account_id = $id")!!.rows.single()[0] as Long
    }

    // ---------------------------------------------------------------- withdraw.sql

    @Test
    fun `withdraw lets one withdrawal through when Ivy's total covers it`() = sessions(restore) {
        withdrawal(a, 109, 8000)
        val log = interleave(withdrawScript(), emptyList())
        assertThat(balances(109, 209)).describedAs(log.joinToString("\n")).containsExactly(-3000L, 5000L)
    }

    @Test
    fun `withdraw refuses a withdrawal larger than Ivy's total`() = sessions(restore) {
        withdrawal(a, 209, 12000)
        val log = interleave(withdrawScript(), emptyList())
        assertThat(balances(109, 209)).describedAs(log.joinToString("\n")).containsExactly(5000L, 5000L)
    }

    @Test
    fun `withdraw lets only one of two withdrawals at the same moment through`() = sessions(restore) {
        withdrawal(a, 109, 8000)
        withdrawal(b, 209, 8000)
        val log = interleave(withdrawScript(), withdrawScript())
        val after = balances(109, 209)
        assertThat(after.sum())
            .describedAs("Ivy's total must stay at or above zero; what happened:\n" + log.joinToString("\n"))
            .isEqualTo(2000L)
        assertThat(after).containsExactlyInAnyOrder(-3000L, 5000L)
    }

    @Test
    fun `withdraw counts all of Ivy's accounts, including a new third one`() = sessions(restore) {
        a.run("INSERT INTO accounts (account_id, kind, customer_id, balance_minor, opened_at) VALUES (409, 'customer', 9, 1000, '2026-07-01 00:00+00')")
        withdrawal(a, 109, 8000)
        withdrawal(b, 209, 8000)
        val log = interleave(withdrawScript(), withdrawScript())
        val after = balances(109, 209, 409)
        // 11,000 in all: the first 8,000 fits, the second does not
        assertThat(after.sum()).describedAs(log.joinToString("\n")).isEqualTo(3000L)
        assertThat(after.take(2)).containsExactlyInAnyOrder(-3000L, 5000L)
    }

    @Test
    fun `withdraw does not refuse Ben's withdrawal because of Ivy's`() = sessions(restore) {
        val ben = balances(202).single()
        withdrawal(a, 109, 8000)
        withdrawal(b, 202, 1000)
        val log = interleave(withdrawScript(), withdrawScript())
        assertThat(balances(109, 202)).describedAs(log.joinToString("\n")).containsExactly(-3000L, ben - 1000)
    }

    // ---------------------------------------------------------------- Retry.kt

    /** A connection with a temporary table that records which attempts committed. Returns Unit, like rollback. */
    private fun withAttemptsTable(block: (Connection) -> Unit): Unit = CourseDb.connect().use { conn ->
        conn.createStatement().use { it.execute("CREATE TEMP TABLE attempts (n int)") }
        block(conn)
    }

    private fun failureOf(block: () -> Unit): SQLException =
        try {
            block()
            throw AssertionError("expected serializable to throw an SQLException")
        } catch (e: SQLException) {
            e
        }

    private fun Connection.insertAttempt(n: Int) = prepareStatement("INSERT INTO attempts VALUES (?)").use { it.setInt(1, n); it.executeUpdate() }

    private fun Connection.attemptsCommitted(): List<Int> = createStatement().use { st ->
        st.executeQuery("SELECT n FROM attempts ORDER BY n").use { rs -> buildList { while (rs.next()) add(rs.getInt(1)) } }
    }

    private fun Connection.isolation(): String = createStatement().use { st ->
        st.executeQuery("SHOW transaction_isolation").use { it.next(); it.getString(1) }
    }

    @Test
    fun `serializable retries a serialization failure and keeps only the attempt that commits`() = withAttemptsTable { conn ->
        val seen = mutableListOf<String>()
        val result = serializable(conn) { attempt ->
            seen += "${conn.autoCommit}/${conn.isolation()}"
            conn.insertAttempt(attempt)
            if (attempt < 3) throw SQLException("could not serialize access due to read/write dependencies among transactions", "40001")
            attempt * 10
        }
        assertThat(result).isEqualTo(30)
        assertThat(seen).describedAs("autocommit/isolation inside each attempt").containsExactly(
            "false/serializable", "false/serializable", "false/serializable",
        )
        assertThat(conn.attemptsCommitted()).describedAs("attempts 1 and 2 were rolled back").containsExactly(3)
    }

    @Test
    fun `serializable retries a deadlock too`() = withAttemptsTable { conn ->
        val result = serializable(conn) { attempt ->
            if (attempt == 1) throw SQLException("deadlock detected", "40P01")
            "ok on attempt $attempt"
        }
        assertThat(result).isEqualTo("ok on attempt 2")
    }

    @Test
    fun `serializable rolls back and rethrows any other error without retrying`() = withAttemptsTable { conn ->
        var attempts = 0
        val e = failureOf {
            serializable(conn) { attempt ->
                attempts++
                conn.insertAttempt(attempt)
                throw SQLException("duplicate key value violates unique constraint", "23505")
            }
        }
        assertThat(e.sqlState).isEqualTo("23505")
        assertThat(attempts).describedAs("a duplicate key is not retried").isEqualTo(1)
        assertThat(conn.attemptsCommitted()).describedAs("the failed attempt was rolled back").isEmpty()
    }

    @Test
    fun `serializable gives up after maxAttempts and rethrows the last failure`() = withAttemptsTable { conn ->
        var attempts = 0
        val e = failureOf {
            serializable(conn, maxAttempts = 3) { attempt ->
                attempts++
                throw SQLException("could not serialize access (attempt $attempt)", "40001")
            }
        }
        assertThat(e.message).describedAs("the last failure is the one rethrown").contains("attempt 3")
        assertThat(attempts).isEqualTo(3)
    }

    @Test
    fun `two withdrawals through serializable leave Ivy's total at or above zero`() {
        val bothHaveRead = CyclicBarrier(2)
        fun withdraw(accountId: Long): Int = CourseDb.connect().use { c ->
            serializable(c) { attempt ->
                val total = c.createStatement().use { st ->
                    st.executeQuery("SELECT sum(balance_minor) FROM accounts WHERE customer_id = 9").use { it.next(); it.getLong(1) }
                }
                if (attempt == 1) bothHaveRead.await(5, TimeUnit.SECONDS)    // both read 10,000 before either writes
                if (total >= 8000) {
                    c.prepareStatement("UPDATE accounts SET balance_minor = balance_minor - 8000 WHERE account_id = ?").use {
                        it.setLong(1, accountId)
                        it.executeUpdate()
                    }
                }
                attempt
            }
        }
        val pool = Executors.newFixedThreadPool(2)
        try {
            val first = pool.submit<Int> { withdraw(109) }
            val second = pool.submit<Int> { withdraw(209) }
            val attempts = listOf(first.get(20, TimeUnit.SECONDS), second.get(20, TimeUnit.SECONDS))
            val after = CourseDb.connect().use { c ->
                c.createStatement().use { st ->
                    st.executeQuery("SELECT balance_minor FROM accounts WHERE account_id IN (109, 209) ORDER BY account_id")
                        .use { rs -> buildList { while (rs.next()) add(rs.getLong(1)) } }
                }
            }
            assertThat(after).describedAs("one withdrawal of 8,000 went through, the other was refused on its retry")
                .containsExactlyInAnyOrder(-3000L, 5000L)
            assertThat(attempts.max()).describedAs("one transaction needed a second attempt").isGreaterThanOrEqualTo(2)
        } finally {
            pool.shutdownNow()
            CourseDb.connect().use { c -> c.createStatement().use { it.execute(restore) } }
        }
    }
}
