package sfz.txn.l07

import java.nio.channels.FileChannel
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardOpenOption
import java.sql.Connection
import java.sql.SQLException

/**
 * Lesson txn-07, exercise 1 of 2: a two-phase commit coordinator over PostgreSQL, and its recovery
 * routine. Exercise 2 is src/main/resources/sfz/txn/l07/in_doubt.sql.
 *
 * Everything in this file is provided except the bodies of [Coordinator.run] and [Coordinator.recover].
 *
 * Check it: ./gradlew :sql:test --tests 'sfz.txn.l07.*'   (from the labs folder)
 */

/**
 * One database that takes part in a distributed transaction, reached through its own connection.
 * The connection is in autocommit mode, so BEGIN, PREPARE TRANSACTION and COMMIT PREPARED are
 * statements you send with [exec].
 */
class Participant(val name: String, val conn: Connection) {

    /** Runs one statement on this participant. A failure throws SQLException with its SQLSTATE. */
    fun exec(sql: String) {
        conn.createStatement().use { it.execute(sql) }
    }

    /**
     * The global id of transaction [txId]'s branch on this participant, such as `txf-1@wallets`.
     * Each participant gets its own gid: PostgreSQL wants gids to be unique across the whole server,
     * and XA does the same with a global id plus a branch qualifier.
     */
    fun gid(txId: String): String = "$txId@$name"

    /** The gids of the transactions prepared in this participant's database and not yet finished, sorted. */
    fun preparedGids(): List<String> =
        conn.createStatement().use { st ->
            st.executeQuery("SELECT gid FROM pg_prepared_xacts WHERE database = current_database() ORDER BY gid").use { rs ->
                buildList { while (rs.next()) add(rs.getString(1)) }
            }
        }
}

/**
 * The coordinator's own durable log. It holds one line per commit decision, `<txId> COMMIT`, and
 * [recordCommit] returns only once that line is on disk, so a crash right after it can't lose the
 * decision. There is no ABORT line: a transaction with no COMMIT line is presumed aborted.
 */
class DecisionLog(val path: Path) {

    /** Appends `<txId> COMMIT` and forces it to disk. Writing this line is the commit point. */
    fun recordCommit(txId: String) {
        FileChannel.open(path, StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.APPEND).use { ch ->
            ch.write(StandardCharsets.UTF_8.encode("$txId COMMIT\n"))
            ch.force(true) // fsync: the decision survives a crash of this process or this machine
        }
    }

    /** True if the log holds a commit decision for [txId]. */
    fun committed(txId: String): Boolean =
        Files.exists(path) && Files.readAllLines(path).any { it == "$txId COMMIT" }
}

/** Where a test makes the coordinator's process "die". */
enum class CrashPoint { NONE, AFTER_PREPARE, AFTER_DECISION, AFTER_FIRST_COMMIT }

/**
 * Thrown at a crash point. It extends Error, not Exception, so that a `catch (e: Exception)` in
 * your code can't swallow it: when a process is killed, none of its catch blocks run either.
 */
class CoordinatorCrashed(val point: CrashPoint) : Error("coordinator crashed at $point")

sealed interface Outcome {
    /** Every participant committed (or will, once recovery runs). */
    data object Committed : Outcome

    /** [participant] voted no: a statement or its PREPARE failed with [sqlState]. Nothing was committed anywhere. */
    data class Aborted(val participant: String, val sqlState: String?) : Outcome
}

/** What [Coordinator.recover] finished: gids committed and gids rolled back, in the order it handled them. */
data class RecoveryReport(val committed: List<String>, val rolledBack: List<String>)

/**
 * A two-phase commit coordinator for the [participants], with its decision [log]. [crashAt] makes
 * it stop dead at one point, for the tests.
 */
class Coordinator(
    private val participants: List<Participant>,
    private val log: DecisionLog,
    private val crashAt: CrashPoint = CrashPoint.NONE,
) {
    /** Provided: simulates this process dying at [point]. Nothing after the call runs. */
    private fun maybeCrash(point: CrashPoint) {
        if (crashAt == point) throw CoordinatorCrashed(point)
    }

    /**
     * Runs transaction [txId] on every participant with two-phase commit. [work] maps a
     * participant's name to the statements it runs (a participant with no entry runs none).
     *
     * 1. Phase 1, prepare: on each participant in list order, send `BEGIN`, its statements, then
     *    `PREPARE TRANSACTION '<gid>'` (use [Participant.gid]). A participant whose PREPARE
     *    succeeds has voted yes: its changes are on disk and it can no longer abort on its own.
     * 2. If a statement or a PREPARE fails with an SQLException, that participant votes no. Send it
     *    `ROLLBACK`, send `ROLLBACK PREPARED '<gid>'` to every participant that already prepared,
     *    and return [Outcome.Aborted] with its name and SQLSTATE. Write nothing to the log.
     * 3. Call `maybeCrash(CrashPoint.AFTER_PREPARE)`.
     * 4. The decision: [DecisionLog.recordCommit]. From here on the transaction is committed, even
     *    if nothing has been told yet. Then call `maybeCrash(CrashPoint.AFTER_DECISION)`.
     * 5. Phase 2, commit: send `COMMIT PREPARED '<gid>'` to each participant in list order, and call
     *    `maybeCrash(CrashPoint.AFTER_FIRST_COMMIT)` right after the first one. Return [Outcome.Committed].
     */
    fun run(txId: String, work: Map<String, List<String>>): Outcome {
        val prepared = mutableListOf<Participant>()
        // phase 1: every participant does its work and votes by preparing
        for (p in participants) {
            try {
                p.exec("BEGIN")
                work[p.name].orEmpty().forEach { p.exec(it) }
                p.exec("PREPARE TRANSACTION '${p.gid(txId)}'") // a yes vote: durable, locks kept
                prepared += p
            } catch (e: SQLException) {
                // a no vote. ROLLBACK ends its open transaction (a failed PREPARE already rolled back,
                // and then ROLLBACK only warns); the ones that said yes are rolled back by gid
                p.exec("ROLLBACK")
                prepared.forEach { it.exec("ROLLBACK PREPARED '${it.gid(txId)}'") }
                return Outcome.Aborted(p.name, e.sqlState) // presumed abort: no log record needed
            }
        }
        maybeCrash(CrashPoint.AFTER_PREPARE)

        log.recordCommit(txId) // the commit point: one fsync'd line in the coordinator's log
        maybeCrash(CrashPoint.AFTER_DECISION)

        // phase 2: tell everyone; a real coordinator retries each one until it answers
        participants.forEachIndexed { i, p ->
            p.exec("COMMIT PREPARED '${p.gid(txId)}'")
            if (i == 0) maybeCrash(CrashPoint.AFTER_FIRST_COMMIT)
        }
        return Outcome.Committed
    }

    /**
     * What a restarted coordinator does before anything else: finish every in-doubt transaction.
     *
     * For each participant in list order, take its prepared gids ([Participant.preparedGids], sorted)
     * that end with `@<participant name>`; leave any other gid alone, because another coordinator
     * owns it. The txId is the part before the `@`. If [log] says the txId committed, send
     * `COMMIT PREPARED '<gid>'`; otherwise send `ROLLBACK PREPARED '<gid>'` (presumed abort).
     * Return the gids you committed and the gids you rolled back, in the order you handled them.
     * Running it again right away finds nothing to do.
     */
    fun recover(): RecoveryReport {
        val committed = mutableListOf<String>()
        val rolledBack = mutableListOf<String>()
        for (p in participants) {
            val suffix = "@${p.name}"
            for (gid in p.preparedGids().filter { it.endsWith(suffix) }) { // only our own branches
                val txId = gid.removeSuffix(suffix)
                if (log.committed(txId)) {
                    p.exec("COMMIT PREPARED '$gid'")   // decided: finish the commit
                    committed += gid
                } else {
                    p.exec("ROLLBACK PREPARED '$gid'") // no decision on disk: presumed abort
                    rolledBack += gid
                }
            }
        }
        return RecoveryReport(committed, rolledBack)
    }
}
