package sfz.txn.l01

import java.sql.Connection
import java.sql.SQLException

/**
 * Lesson txn-01, exercise 2 of 2: the retry loop that SERIALIZABLE needs. Reference answer.
 *
 * Runs [work] as one SERIALIZABLE transaction on [conn] and commits it, retrying the whole
 * transaction on 40001 and 40P01, at most [maxAttempts] attempts in all.
 */
fun <T> serializable(conn: Connection, maxAttempts: Int = 5, work: (attempt: Int) -> T): T {
    require(maxAttempts >= 1) { "maxAttempts must be at least 1" }
    conn.autoCommit = false                                       // the transaction ends where we say
    conn.transactionIsolation = Connection.TRANSACTION_SERIALIZABLE
    var attempt = 1
    while (true) {
        try {
            val result = work(attempt)
            conn.commit()                                         // SSI often reports the conflict here,
            return result                                         // so COMMIT belongs inside the try
        } catch (e: SQLException) {
            conn.rollback()                                       // throw the whole attempt away
            val retryable = e.sqlState == "40001" || e.sqlState == "40P01"
            if (!retryable || attempt >= maxAttempts) throw e
            attempt++                                             // and run all of it again: the next
        } catch (e: Throwable) {                                  // attempt reads fresh data
            conn.rollback()
            throw e
        }
    }
}

// In a service, add a short random sleep before each retry (a few milliseconds, growing with
// the attempt) so two transactions that keep colliding stop doing it in lockstep, and keep
// side effects outside the work block: an HTTP call or a Kafka send inside it would run once
// per attempt.
