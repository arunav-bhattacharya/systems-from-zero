package sfz.sql.l10

import java.sql.Connection
import java.sql.ResultSet
import java.time.Instant

/** One line of the merchant dashboard: a merchant and its latest succeeded payment, if it has one. */
data class LatestPayment(
    val merchantId: Long,
    val merchantName: String,
    val paymentId: Long?,
    val amountMinor: Long?,
    val createdAt: Instant?,
)

/** Lesson sql-10, exercise 4 of 5: the N+1 query, as one query. Reference answer. */
fun latestPayments(conn: Connection): List<LatestPayment> =
    conn.prepareStatement(
        """
        SELECT m.merchant_id, m.name, p.payment_id, p.amount_minor, p.created_at
        FROM merchants m
        LEFT JOIN LATERAL (                       -- runs once per merchant, inside the server
            SELECT payment_id, amount_minor, created_at
            FROM payments
            WHERE merchant_id = m.merchant_id AND status = 'succeeded'
            ORDER BY created_at DESC, payment_id DESC
            LIMIT 1
        ) p ON true                               -- LEFT ... ON true keeps merchants with no payment
        ORDER BY m.merchant_id
        """,
    ).use { ps ->
        ps.executeQuery().use { rs ->
            buildList {
                while (rs.next()) {
                    add(
                        LatestPayment(
                            merchantId = rs.getLong(1),
                            merchantName = rs.getString(2),
                            paymentId = rs.longOrNull(3),                    // NULL stays null, not 0
                            amountMinor = rs.longOrNull(4),
                            createdAt = rs.getTimestamp(5)?.toInstant(),
                        ),
                    )
                }
            }
        }
    }
/** getLong returns 0 for NULL; wasNull says which one it was. */
private fun ResultSet.longOrNull(column: Int): Long? = getLong(column).takeUnless { wasNull() }

// The two-query version, which is what an ORM's batch fetching sends:
//   SELECT merchant_id, name FROM merchants ORDER BY merchant_id
//   SELECT DISTINCT ON (merchant_id) merchant_id, payment_id, amount_minor, created_at
//   FROM payments WHERE merchant_id = ANY (?) AND status = 'succeeded'
//   ORDER BY merchant_id, created_at DESC, payment_id DESC
// with conn.createArrayOf("bigint", ids.toTypedArray()) bound to the ?. The loop moves into
// the server either way; the number of round trips stops growing with the number of merchants.
