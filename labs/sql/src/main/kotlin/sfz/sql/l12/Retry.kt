package sfz.sql.l12

import java.sql.Connection

/**
 * Lesson sql-12, exercise 2 of 2: the retry loop that SERIALIZABLE needs.
 *
 * Runs [work] as one SERIALIZABLE transaction on [conn] and commits it, then returns what [work]
 * returned. [work] gets the attempt number, starting at 1, and runs its statements on [conn].
 *
 * - Before the first attempt, turn autocommit off and set the isolation level to SERIALIZABLE.
 * - If [work] or the COMMIT fails with an SQLException whose SQLSTATE is 40001 (serialization
 *   failure) or 40P01 (deadlock), roll back and run [work] again from the start, as a new
 *   transaction. Make at most [maxAttempts] attempts in all; if the last one fails, rethrow
 *   its exception.
 * - On any other exception, roll back and rethrow it at once: a duplicate key or a bug does
 *   not go away by trying again.
 *
 * Check it: ./gradlew :sql:test --tests 'sfz.sql.l12.*'   (from the labs folder)
 */
fun <T> serializable(conn: Connection, maxAttempts: Int = 5, work: (attempt: Int) -> T): T =
    TODO("lesson sql-12: run work in a SERIALIZABLE transaction, commit, and retry on 40001 and 40P01")
