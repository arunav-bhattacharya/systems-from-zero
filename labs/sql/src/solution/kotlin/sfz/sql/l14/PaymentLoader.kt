package sfz.sql.l14

import com.zaxxer.hikari.HikariConfig
import java.sql.Connection
import java.sql.Statement
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

/** Lesson sql-14, exercise 2 of 5: the pool for the payment importer. Reference answer. */
fun poolConfig(jdbcUrl: String, username: String, password: String): HikariConfig =
    HikariConfig().apply {
        this.jdbcUrl = jdbcUrl
        this.username = username
        this.password = password
        poolName = "importer"
        maximumPoolSize = 4                 // (2 cores x 2) + 0 spindles: the data is cached
        minimumIdle = 4                     // a fixed pool: no opening connections under load
        connectionTimeout = 2_000           // a borrower waits 2 s, then gets SQLTransientConnectionException
        addDataSourceProperty("reWriteBatchedInserts", "true")   // a batch becomes multi-row INSERTs
    }

/** Lesson sql-14, exercise 3 of 5: insert many payments in a few round trips. Reference answer. */
fun insertPayments(conn: Connection, payments: List<NewPayment>): Int {
    if (payments.isEmpty()) return 0
    conn.prepareStatement(
        "INSERT INTO payments (card_id, merchant_id, amount_minor, status, created_at) VALUES (?, ?, ?, ?, ?)",
    ).use { ps ->
        for (p in payments) {
            ps.setLong(1, p.cardId)
            ps.setLong(2, p.merchantId)
            ps.setLong(3, p.amountMinor)
            ps.setString(4, p.status)
            ps.setTimestamp(5, Timestamp.from(p.createdAt))
            ps.addBatch()                                      // queued in the driver, nothing sent yet
        }
        val counts = ps.executeBatch()                         // sent together; the driver reads the
                                                               // answers only when its buffer fills
        // with reWriteBatchedInserts the driver reports SUCCESS_NO_INFO (-2) per row: count those as 1
        return counts.sumOf { if (it == Statement.SUCCESS_NO_INFO) 1 else it }
    }
}
// For a bulk load of millions of rows, COPY (pgJDBC's CopyManager) is faster still: one
// statement streams all the rows. Batches suit what an application inserts in a request.
