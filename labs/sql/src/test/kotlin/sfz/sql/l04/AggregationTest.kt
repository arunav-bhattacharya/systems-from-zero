package sfz.sql.l04

import org.junit.jupiter.api.Test
import sfz.sql.support.rollback
import sfz.sql.support.row
import java.math.BigDecimal

/**
 * Lesson sql-04. Your queries are in src/main/resources/sfz/sql/l04/. Each test runs in a
 * transaction that is rolled back, so rows a test adds never reach the next test.
 */
class AggregationTest {

    private fun pct(s: String) = BigDecimal(s)

    @Test
    fun `merchant_status_report has one row per merchant with per-status counts`() = rollback {
        val rows = exercise("sql/l04", "merchant_status_report")
        rows.assertColumns("merchant_id", "name", "payments", "succeeded", "failed", "failed_pct")
        rows.assertRowsInOrder(
            row(1, "Northwind Grocers", 8, 7, 0, 0),             // one payment is pending
            row(2, "Blue Fern Cafe", 6, 3, 3, 50),
            row(3, "Metro Transit", 5, 4, 0, 0),
            row(4, "Volt Electronics", 8, 7, 1, pct("12.5")),     // 100 * 1 / 8 in integers is 12
            row(5, "Harbor Hotel", 6, 6, 0, 0),
            row(6, "Paper Lantern Books", 0, 0, 0, null),        // no payments: count(*) after a LEFT JOIN says 1
            row(7, "Quick Bite", 4, 3, 1, 25),
            row(8, "Sunrise Grocers", 0, 0, 0, null),
        )
    }

    @Test
    fun `merchant_status_report follows new rows`() = rollback {
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES " +
                "(100, 1, 8, 999, 'failed', '2026-07-01 12:00+00'), " +
                "(101, 2, 8, 450, 'succeeded', '2026-07-01 12:05+00'), " +
                "(102, 2, 8, 450, 'pending', '2026-07-01 12:10+00')",
        )
        exercise("sql/l04", "merchant_status_report").assertRowsInOrder(
            row(1, "Northwind Grocers", 8, 7, 0, 0),
            row(2, "Blue Fern Cafe", 6, 3, 3, 50),
            row(3, "Metro Transit", 5, 4, 0, 0),
            row(4, "Volt Electronics", 8, 7, 1, pct("12.5")),
            row(5, "Harbor Hotel", 6, 6, 0, 0),
            row(6, "Paper Lantern Books", 0, 0, 0, null),
            row(7, "Quick Bite", 4, 3, 1, 25),
            row(8, "Sunrise Grocers", 3, 1, 1, pct("33.3")),     // 1 of 3, rounded to one place
        )
    }

    @Test
    fun `quarterly_channel_rollup adds a subtotal per quarter and a grand total`() = rollback {
        val rows = exercise("sql/l04", "quarterly_channel_rollup")
        rows.assertColumns("quarter", "channel", "payments", "volume_minor")
        rows.assertRowsInOrder(
            row("2026-Q1", "android", 3, 40498),
            row("2026-Q1", "ios", 4, 23664),
            row("2026-Q1", "pos", 4, 11980),
            row("2026-Q1", "web", 7, 384649),
            row("2026-Q1", "all", 18, 460791),
            row("2026-Q2", "android", 1, 1720),
            row("2026-Q2", "ios", 2, 3915),
            row("2026-Q2", "pos", 4, 10580),
            row("2026-Q2", "web", 5, 243449),
            row("2026-Q2", "all", 12, 259664),
            row("all", "all", 30, 720455),
        )
    }

    @Test
    fun `quarterly_channel_rollup keeps a missing channel apart from the subtotal`() = rollback {
        // metadata defaults to '{}', so this payment has no channel: its group key is NULL
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) " +
                "VALUES (100, 1, 1, 1000, 'succeeded', '2026-05-05 10:00+00')",
        )
        exercise("sql/l04", "quarterly_channel_rollup").assertRowsInOrder(
            row("2026-Q1", "android", 3, 40498),
            row("2026-Q1", "ios", 4, 23664),
            row("2026-Q1", "pos", 4, 11980),
            row("2026-Q1", "web", 7, 384649),
            row("2026-Q1", "all", 18, 460791),
            row("2026-Q2", "android", 1, 1720),
            row("2026-Q2", "ios", 2, 3915),
            row("2026-Q2", "pos", 4, 10580),
            row("2026-Q2", "web", 5, 243449),
            row("2026-Q2", null, 1, 1000),                    // a real NULL group, not a subtotal
            row("2026-Q2", "all", 13, 260664),
            row("all", "all", 31, 721455),
        )
    }

    @Test
    fun `customer_net_spend counts each payment once`() = rollback {
        val rows = exercise("sql/l04", "customer_net_spend")
        rows.assertColumns("customer_id", "full_name", "paid_minor", "refunded_minor", "net_minor")
        rows.assertRowsInOrder(
            row(1, "Asha Rao", 120555, 0, 120555),
            row(2, "Ben Carter", 170768, 3880, 166888),          // two accounts, three cards
            row(3, "Chloe Martin", 20914, 0, 20914),
            row(4, "Daniel Kim", 133625, 129900, 3725),
            row(5, "Elena Petrova", 71450, 18000, 53450),        // payment 5 has two refunds: 119450 if counted twice
            row(6, "Farid Haddad", 39718, 18999, 20719),         // payments 17 and 18 are both 18999
            row(7, "Grace Lee", 1100, 0, 1100),                  // 275 + 275 + 550
            row(10, "Jonas Weber", 86000, 0, 86000),
            row(13, "Mateo Ruiz", 76325, 25000, 51325),
        )
    }

    @Test
    fun `customer_net_spend follows new rows`() = rollback {
        // payment 13 (Ben, 64000) gets two partial refunds
        update(
            "INSERT INTO refunds (refund_id, payment_id, amount_minor, reason, created_at) VALUES " +
                "(50, 13, 1000, 'customer_request', '2026-03-05 10:00+00'), " +
                "(51, 13, 2000, 'customer_request', '2026-03-06 10:00+00')",
        )
        exercise("sql/l04", "customer_net_spend").assertRowsInOrder(
            row(1, "Asha Rao", 120555, 0, 120555),
            row(2, "Ben Carter", 170768, 6880, 163888),
            row(3, "Chloe Martin", 20914, 0, 20914),
            row(4, "Daniel Kim", 133625, 129900, 3725),
            row(5, "Elena Petrova", 71450, 18000, 53450),
            row(6, "Farid Haddad", 39718, 18999, 20719),
            row(7, "Grace Lee", 1100, 0, 1100),
            row(10, "Jonas Weber", 86000, 0, 86000),
            row(13, "Mateo Ruiz", 76325, 25000, 51325),
        )
    }
}
