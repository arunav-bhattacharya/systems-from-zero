package sfz.sql.l14

import java.sql.Connection
import java.time.Instant

/** One line of the merchant dashboard: a merchant and its latest succeeded payment, if it has one. */
data class LatestPayment(
    val merchantId: Long,
    val merchantName: String,
    val paymentId: Long?,
    val amountMinor: Long?,
    val createdAt: Instant?,
)

/**
 * Lesson sql-14, exercise 4 of 5: the N+1 query (a trap).
 *
 * Returns every merchant, by merchant_id, with its latest succeeded payment (latest created_at,
 * then the highest payment_id), or nulls when it has none.
 *
 * The placeholder is what an ORM's lazy loading does: one query for the merchants, then one
 * more query for each merchant. The answer is right, but 8 merchants cost 9 round trips and
 * 2,500 merchants would cost 2,501. Fetch it all in one query (LEFT JOIN LATERAL ... LIMIT 1 from
 * lesson 9, or DISTINCT ON), or in two: the merchants, then all their payments at once with
 * `merchant_id = ANY (?)`. The tests allow at most two round trips.
 */
fun latestPayments(conn: Connection): List<LatestPayment> {
    val merchants = conn.prepareStatement("SELECT merchant_id, name FROM merchants ORDER BY merchant_id").use { ps ->
        ps.executeQuery().use { rs -> buildList { while (rs.next()) add(rs.getLong(1) to rs.getString(2)) } }
    }
    return merchants.map { (id, name) ->
        conn.prepareStatement(
            """
            SELECT payment_id, amount_minor, created_at
            FROM payments
            WHERE merchant_id = ? AND status = 'succeeded'
            ORDER BY created_at DESC, payment_id DESC
            LIMIT 1
            """,
        ).use { ps ->
            ps.setLong(1, id)                                  // one more round trip per merchant
            ps.executeQuery().use { rs ->
                if (rs.next()) {
                    LatestPayment(id, name, rs.getLong(1), rs.getLong(2), rs.getTimestamp(3).toInstant())
                } else {
                    LatestPayment(id, name, null, null, null)
                }
            }
        }
    }
}
