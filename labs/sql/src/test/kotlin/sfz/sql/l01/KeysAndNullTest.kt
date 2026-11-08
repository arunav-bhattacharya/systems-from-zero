package sfz.sql.l01

import org.junit.jupiter.api.Test
import sfz.sql.support.rollback
import sfz.sql.support.row

/**
 * Lesson sql-01. Each test runs your query from src/main/resources/sfz/sql/l01/ against the
 * seeded course database, inside a transaction that is rolled back afterwards.
 */
class KeysAndNullTest {

    private val addTwoCustomers = """
        INSERT INTO customers (customer_id, email, full_name, country_code, referred_by, created_at) VALUES
            (50, 'new.organic@example.com',  'New Organic',  'US', NULL, '2026-07-01 10:00+00'),
            (51, 'new.referred@example.com', 'New Referred', 'GB', 13,   '2026-07-01 11:00+00')
    """

    @Test
    fun `not_referred_by_asha keeps the customers nobody referred`() = rollback {
        val rows = exercise("sql/l01", "not_referred_by_asha")
        rows.assertColumns("customer_id")
        // 3 and 5 were referred by Asha; 1, 2, 7, 9 and 11 have referred_by NULL and still count
        rows.assertRowsInOrder(
            row(1), row(2), row(4), row(6), row(7), row(8), row(9), row(10), row(11), row(12), row(13),
        )
    }

    @Test
    fun `not_referred_by_asha follows new rows`() = rollback {
        update(addTwoCustomers)
        update(
            "INSERT INTO customers (customer_id, email, full_name, country_code, referred_by, created_at) " +
                "VALUES (52, 'asha.friend@example.com', 'Asha Friend', 'IN', 1, '2026-07-02 09:00+00')",
        )
        exercise("sql/l01", "not_referred_by_asha").assertRowsInOrder(
            row(1), row(2), row(4), row(6), row(7), row(8), row(9), row(10), row(11), row(12), row(13), row(50), row(51),
        )
    }

    @Test
    fun `customer_counts tells rows, non-NULL values and distinct values apart`() = rollback {
        val rows = exercise("sql/l01", "customer_counts")
        rows.assertColumns("customers", "referred", "referrers", "organic")
        // 13 rows, 8 with a referrer, 7 different referrers (Asha referred two), 5 with NULL
        rows.assertRowsInOrder(row(13, 8, 7, 5))
    }

    @Test
    fun `customer_counts follows new rows`() = rollback {
        update(addTwoCustomers)   // one organic, one referred by a first-time referrer
        exercise("sql/l01", "customer_counts").assertRowsInOrder(row(15, 9, 8, 6))
    }

    @Test
    fun `march_top_payments uses a half-open month, skips failed payments and orders ties by id`() = rollback {
        val rows = exercise("sql/l01", "march_top_payments")
        rows.assertColumns("payment_id", "merchant_id", "amount_minor", "band")
        // 13 is at 00:00 on 1 March (in), 22 at 23:59:59.5 on 31 March (in), 23 at 00:00 on 1 April (out),
        // 15 is larger but failed; 17, 18 and 19 tie on 18999, and the smallest ids win the last two places
        rows.assertRowsInOrder(
            row(13, 5, 64000, "large"),
            row(22, 5, 52000, "large"),
            row(16, 5, 31500, "medium"),
            row(17, 4, 18999, "medium"),
            row(18, 4, 18999, "medium"),
        )
    }

    @Test
    fun `march_top_payments labels small amounts and reads status from the data`() = rollback {
        // fail every March payment of 100.00 or more: only two small ones are left
        update(
            "UPDATE payments SET status = 'failed' " +
                "WHERE amount_minor >= 10000 AND created_at >= '2026-03-01' AND created_at < '2026-04-01'",
        )
        exercise("sql/l01", "march_top_payments").assertRowsInOrder(
            row(14, 1, 5310, "small"),
            row(21, 7, 1325, "small"),
        )
    }
}
