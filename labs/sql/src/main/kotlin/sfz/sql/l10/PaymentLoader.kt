package sfz.sql.l10

import com.zaxxer.hikari.HikariConfig
import java.sql.Connection
import java.sql.Timestamp
import java.time.Instant

/** A payment to insert. payment_id and payment_uid come from their column defaults. */
data class NewPayment(
    val cardId: Long,
    val merchantId: Long,
    val amountMinor: Long,
    val status: String,
    val createdAt: Instant,
)

/**
 * Lesson sql-10, exercise 2 of 5: the pool for the payment importer.
 *
 * The importer's database has 2 cores and its data fits in memory, so the pool sizing formula
 * gives (2 x 2) + 0 = 4 connections. Return a HikariConfig for [jdbcUrl], [username] and
 * [password] with:
 * - at most 4 connections (maximumPoolSize), all kept open (minimumIdle the same),
 * - a borrower that gives up after 2 seconds when all 4 are busy (connectionTimeout, in ms),
 * - pgJDBC's reWriteBatchedInserts switched on, so a batch of INSERTs reaches the server as a
 *   few multi-row INSERTs (addDataSourceProperty("reWriteBatchedInserts", "true")),
 * - the pool name "importer" (poolName), which Hikari's log lines and errors carry.
 * The placeholder sets only the URL and the login, so Hikari's defaults apply: 10 connections
 * and a 30-second wait.
 */
fun poolConfig(jdbcUrl: String, username: String, password: String): HikariConfig =
    HikariConfig().apply {
        this.jdbcUrl = jdbcUrl
        this.username = username
        this.password = password
    }

/**
 * Lesson sql-10, exercise 3 of 5: insert many payments in a few round trips (a trap).
 *
 * Inserts [payments] into payments on [conn] and returns how many rows it inserted. [conn] is
 * already in a transaction (autocommit off); don't commit.
 *
 * The placeholder is correct and uses a PreparedStatement, but it calls executeUpdate once per
 * payment, so 1,000 payments cost 1,000 round trips: the driver sends one INSERT and waits for
 * the answer before it sends the next. Queue the rows with addBatch and send them with one
 * executeBatch. The tests count round trips, not milliseconds.
 */
fun insertPayments(conn: Connection, payments: List<NewPayment>): Int {
    var inserted = 0
    conn.prepareStatement(
        "INSERT INTO payments (card_id, merchant_id, amount_minor, status, created_at) VALUES (?, ?, ?, ?, ?)",
    ).use { ps ->
        for (p in payments) {
            ps.setLong(1, p.cardId)
            ps.setLong(2, p.merchantId)
            ps.setLong(3, p.amountMinor)
            ps.setString(4, p.status)
            ps.setTimestamp(5, Timestamp.from(p.createdAt))
            inserted += ps.executeUpdate()                     // one round trip per payment
        }
    }
    return inserted
}
