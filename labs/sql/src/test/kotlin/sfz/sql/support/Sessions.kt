package sfz.sql.support

import org.opentest4j.AssertionFailedError
import java.sql.Connection
import java.sql.SQLException
import java.sql.Statement
import java.util.concurrent.ExecutionException
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.Future
import java.util.concurrent.TimeUnit

/**
 * Two sessions on the seeded database at the same time, for the lessons on upserts, isolation and
 * row locks ([Sessions.session] adds more, for several workers on one job queue).
 *
 * Unlike [rollback], these sessions run in autocommit mode and COMMIT for real, because one
 * session can only see another's work after it commits. So [sessions] always runs [cleanup]
 * at the end, pass or fail, on a fresh connection, to put the seed back the way it was.
 *
 * Nothing here sleeps. Statements run in exactly the order the test calls them, and a statement
 * that has to wait for another session's lock is started with [Session.start]; [Pending.awaitBlocked]
 * returns once PostgreSQL reports that it is waiting:
 * ```
 * sessions(cleanup = "UPDATE accounts SET balance_minor = 5000 WHERE customer_id = 9") {
 *     a.run("BEGIN ISOLATION LEVEL REPEATABLE READ")
 *     b.run("BEGIN ISOLATION LEVEL REPEATABLE READ")
 *     a.run("UPDATE accounts SET balance_minor = 4000 WHERE account_id = 109")
 *     val waiting = b.start("UPDATE accounts SET balance_minor = 4000 WHERE account_id = 109")
 *     waiting.awaitBlocked()                      // B waits for A's row lock
 *     a.run("COMMIT")
 *     assertThat(waiting.sqlState()).isEqualTo("40001")
 * }
 * ```
 * It returns Unit for the same reason [rollback] does: an expression-bodied JUnit test takes its
 * return type from here.
 */
fun sessions(cleanup: String, block: Sessions.() -> Unit): Unit {
    val s = Sessions()
    try {
        s.block()
    } finally {
        s.close()
        CourseDb.connect().use { conn -> conn.createStatement().use { it.execute(cleanup) } }
    }
}

class Sessions internal constructor() : AutoCloseable {
    private val monitor: Connection = CourseDb.connect()
    val a = Session("A", monitor)
    val b = Session("B", monitor)
    private val extra = mutableListOf<Session>()

    /**
     * One more session besides [a] and [b], for tests with several workers (txn-02's job queue).
     * It is closed with the others. Its application_name is [name], so pg_stat_activity shows it
     * and SQL can read it with current_setting('application_name').
     */
    fun session(name: String): Session = Session(name, monitor).also { extra += it }

    /**
     * Runs two scripts in two sessions, one statement at a time, taking turns: A's first statement,
     * then B's first, then A's second, and so on. When a statement has to wait for a lock, the
     * other session carries on until the lock is released. When a statement fails with a
     * serialization failure (40001) or a deadlock (40P01), that session rolls back and, once the
     * other session has finished, runs its whole script again from the start: the retry loop an
     * application needs. It gives up after [maxAttempts] attempts. Any other error fails the test.
     *
     * Returns a log of what happened, one line per statement, for assertion messages.
     */
    fun interleave(scriptA: List<String>, scriptB: List<String>, maxAttempts: Int = 3): List<String> {
        val log = mutableListOf<String>()
        val runs = listOf(Run(a, scriptA), Run(b, scriptB))
        var turn = 0
        var guard = 0
        while (runs.any { !it.done }) {
            if (++guard > 1000) throw AssertionFailedError("interleave did not finish:\n" + log.joinToString("\n"))
            val me = runs[turn]
            val other = runs[1 - turn]
            if (me.done) {
                turn = 1 - turn
                continue
            }
            if (me.retryLater && !other.done && !other.retryLater) {
                turn = 1 - turn                      // retry alone, after the other session is done
                continue
            }
            me.retryLater = false
            val pending = me.pending ?: me.session.start(me.script[me.next]).also {
                me.pending = it
                log += "${me.session.name}: ${oneLine(me.script[me.next])}"
            }
            // let it finish, or stop once it is waiting for a lock and the other session can move
            val blocked = pending.awaitDoneOrBlocked()
            if (blocked && !other.done && other.pending == null) {
                log += "${me.session.name}:   ...waits for a lock"
                turn = 1 - turn
                continue
            }
            if (blocked && other.pending != null) {
                // both are waiting: PostgreSQL's deadlock detector ends one of them within a second
                pending.awaitDone(10)
            }
            pending.awaitDone(10)
            me.pending = null
            val state = pending.sqlStateOrNull()
            when {
                state == null -> {
                    log += "${me.session.name}:   -> ${pending.summary()}"
                    me.next++
                    if (me.next == me.script.size) me.done = true
                }
                state == "40001" || state == "40P01" -> {
                    log += "${me.session.name}:   -> ERROR $state: ${pending.errorMessage()}"
                    me.session.rollbackQuietly()
                    me.attempt++
                    if (me.attempt > maxAttempts) {
                        throw AssertionFailedError("session ${me.session.name} failed $maxAttempts times:\n" + log.joinToString("\n"))
                    }
                    log += "${me.session.name}:   rolls back; will retry its whole script (attempt ${me.attempt})"
                    me.next = 0
                    me.retryLater = !other.done
                }
                else -> throw AssertionFailedError(
                    "session ${me.session.name} failed with SQLSTATE $state: ${pending.errorMessage()}\n" + log.joinToString("\n"),
                )
            }
            turn = 1 - turn
        }
        return log
    }

    private class Run(val session: Session, val script: List<String>) {
        var next = 0
        var attempt = 1
        var done = script.isEmpty()
        var pending: Pending? = null
        var retryLater = false
    }

    override fun close() {
        extra.forEach { it.close() }
        a.close()
        b.close()
        monitor.close()
    }

    companion object {
        private fun oneLine(sql: String) = sql.replace(Regex("\\s+"), " ").trim().let { if (it.length > 90) it.take(87) + "..." else it }
    }
}

/** One session: its own connection, in autocommit mode, so BEGIN and COMMIT are statements you run. */
class Session internal constructor(val name: String, private val monitor: Connection) : AutoCloseable {
    val conn: Connection = CourseDb.connect().also { c ->
        c.createStatement().use {
            // a forgotten COMMIT fails the test instead of hanging it
            it.execute("SET lock_timeout = '8s'")
            it.execute("SET statement_timeout = '15s'")
            // pg_stat_activity and current_setting('application_name') show the session's name
            it.execute("SET application_name = '${name.replace("'", "''")}'")
        }
    }
    val pid: Int = conn.createStatement().use { st -> st.executeQuery("SELECT pg_backend_pid()").use { it.next(); it.getInt(1) } }
    private val worker: ExecutorService = Executors.newSingleThreadExecutor { r -> Thread(r, "session-$name").apply { isDaemon = true } }
    private var current: Pending? = null

    /** Runs [sql] (one or more statements) now and returns the rows of the last query, if any. Fails the test on an error. */
    fun run(sql: String): Rows? {
        val p = start(sql)
        p.awaitDone(15)
        return p.result()
    }

    /**
     * Runs [sql] now and returns its rows, like [run], but fails the test as soon as the statement
     * waits for a lock held by another session (the waiting statement is cancelled first).
     * Use it to check that a statement never queues behind another transaction.
     */
    fun runWithoutWaiting(sql: String): Rows? {
        val p = start(sql)
        if (p.awaitDoneOrBlocked()) {
            val holders = blockers()
            cancel()
            p.awaitDone(15)
            throw AssertionFailedError(
                "session $name waited for a lock held by ${holders.joinToString { "session " + it }} instead of moving on:\n  $sql",
            )
        }
        return p.result()
    }

    /** The names of the sessions whose locks this session is waiting for (from pg_blocking_pids). */
    fun blockers(): List<String> =
        monitor.prepareStatement(
            "SELECT b.application_name FROM pg_stat_activity b WHERE b.pid = ANY (pg_blocking_pids(?)) ORDER BY 1",
        ).use { ps ->
            ps.setInt(1, pid)
            ps.executeQuery().use { rs -> buildList { while (rs.next()) add(rs.getString(1)) } }
        }

    /** Cancels the statement this session is running (pg_cancel_backend); it fails with 57014. */
    fun cancel() {
        monitor.prepareStatement("SELECT pg_cancel_backend(?)").use { ps ->
            ps.setInt(1, pid)
            ps.executeQuery().close()
        }
    }

    /** Runs [sql] now and returns null if it succeeded, or the SQLSTATE it failed with. */
    fun sqlStateOf(sql: String): String? {
        val p = start(sql)
        p.awaitDone(15)
        return p.sqlStateOrNull()
    }

    /** Starts [sql] on this session's own thread and returns at once. Use it for a statement that will wait for a lock. */
    fun start(sql: String): Pending {
        check(current?.isDone != false) { "session $name is still running its previous statement" }
        val future = worker.submit<Outcome> { execute(sql) }
        return Pending(this, sql, future).also { current = it }
    }

    /** True while this session's statement waits for a lock held by another transaction. */
    fun isWaitingForLock(): Boolean =
        monitor.prepareStatement("SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid = ?").use { ps ->
            ps.setInt(1, pid)
            ps.executeQuery().use { rs -> rs.next() && rs.getBoolean(1) }
        }

    internal fun rollbackQuietly() {
        try {
            conn.createStatement().use { it.execute("ROLLBACK") }
        } catch (_: SQLException) {
        }
    }

    private fun execute(sql: String): Outcome = try {
        conn.createStatement().use { st ->
            var last: Rows? = null
            var count = -1
            var isResult = st.execute(sql)
            while (true) {
                if (isResult) {
                    st.resultSet.use { last = Rows.from(it) }
                } else if (st.updateCount == -1) {
                    break
                } else {
                    count = st.updateCount
                }
                isResult = st.getMoreResults(Statement.CLOSE_CURRENT_RESULT)
            }
            Outcome(last, count, null)
        }
    } catch (e: SQLException) {
        Outcome(null, -1, e)
    }

    override fun close() {
        worker.shutdownNow()
        try {
            if (!conn.isClosed) conn.close()
        } catch (_: SQLException) {
        }
    }

    internal class Outcome(val rows: Rows?, val updateCount: Int, val error: SQLException?)
}

/** A statement that may still be running in its session. */
class Pending internal constructor(private val session: Session, private val sql: String, private val future: Future<Session.Outcome>) {

    private companion object {
        val WRITES = Regex("""^\s*(WITH\b.*\b)?(INSERT|UPDATE|DELETE|MERGE)\b""", setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL))
    }

    val isDone: Boolean get() = future.isDone

    /** Waits until the statement is waiting for a lock. Fails the test if it finishes instead, or after 5 seconds. */
    fun awaitBlocked() {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
        while (System.nanoTime() < deadline) {
            if (future.isDone) {
                throw AssertionFailedError("expected session ${session.name} to wait for a lock, but it finished: ${summary()}\n  $sql")
            }
            if (session.isWaitingForLock()) return
            Thread.sleep(5)
        }
        throw AssertionFailedError("session ${session.name} neither finished nor waited for a lock within 5 s:\n  $sql")
    }

    /** Waits until the statement finishes or waits for a lock; returns true if it is waiting. */
    fun awaitDoneOrBlocked(): Boolean {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10)
        while (System.nanoTime() < deadline) {
            if (future.isDone) return false
            if (session.isWaitingForLock()) return true
            Thread.sleep(5)
        }
        throw AssertionFailedError("session ${session.name} took more than 10 s:\n  $sql")
    }

    internal fun awaitDone(seconds: Long) {
        try {
            future.get(seconds, TimeUnit.SECONDS)
        } catch (e: java.util.concurrent.TimeoutException) {
            throw AssertionFailedError("session ${session.name} did not finish within $seconds s (is another session holding a lock?):\n  $sql")
        } catch (e: ExecutionException) {
            throw AssertionFailedError("session ${session.name} crashed: ${e.cause}", e.cause)
        }
    }

    private fun outcome(): Session.Outcome {
        awaitDone(15)
        return future.get()
    }

    /** Waits for the statement and returns its rows (null if it returned none). Fails the test if it failed. */
    fun result(): Rows? {
        val o = outcome()
        o.error?.let { throw AssertionFailedError("session ${session.name} failed with SQLSTATE ${it.sqlState}: ${it.message}\n  $sql", it) }
        return o.rows
    }

    /** Waits for the statement and returns null if it succeeded, or the SQLSTATE it failed with. */
    fun sqlState(): String? = sqlStateOrNull()

    /** Waits for the statement and returns its update count (-1 if it was a query). Fails the test if it failed. */
    fun updateCount(): Int {
        result()
        return outcome().updateCount
    }

    internal fun sqlStateOrNull(): String? = outcome().error?.let { it.sqlState ?: "unknown" }

    internal fun errorMessage(): String = outcome().error?.message?.lineSequence()?.first() ?: ""

    internal fun summary(): String {
        if (!future.isDone) return "still running"
        val o = future.get()
        return when {
            o.error != null -> "ERROR ${o.error.sqlState}"
            o.rows != null -> "${o.rows.size} row${if (o.rows.size == 1) "" else "s"}" +
                (if (o.rows.size == 1 && o.rows.columns.size <= 3) " ${o.rows.rows[0]}" else "")
            o.updateCount >= 0 && WRITES.containsMatchIn(sql) -> "${o.updateCount} row${if (o.updateCount == 1) "" else "s"} changed"
            else -> "ok"
        }
    }
}

/**
 * Splits an exercise file into statements at the semicolons that end them, so a test can run the
 * statements one at a time. Drops -- comments and blank statements. It does not understand
 * dollar-quoting, which the exercises never use.
 */
fun splitStatements(sql: String): List<String> {
    val out = mutableListOf<String>()
    val cur = StringBuilder()
    var i = 0
    var inQuote = false
    while (i < sql.length) {
        val c = sql[i]
        when {
            inQuote -> {
                cur.append(c)
                if (c == '\'') inQuote = false
            }
            c == '\'' -> {
                inQuote = true
                cur.append(c)
            }
            c == '-' && i + 1 < sql.length && sql[i + 1] == '-' -> {
                while (i < sql.length && sql[i] != '\n') i++
                cur.append('\n')
            }
            c == ';' -> {
                if (cur.isNotBlank()) out += cur.toString().trim()
                cur.clear()
            }
            else -> cur.append(c)
        }
        i++
    }
    if (cur.isNotBlank()) out += cur.toString().trim()
    return out
}
