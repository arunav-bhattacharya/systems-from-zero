package sfz.sql.l09

import org.junit.jupiter.api.Test
import sfz.sql.support.rollback
import sfz.sql.support.row
import java.time.Instant

/**
 * Lesson sql-09. Your queries are in src/main/resources/sfz/sql/l09/. Each test runs in a
 * transaction that is rolled back, so the rows a test adds are gone before the next one starts.
 */
class LateralAndPagingTest {

    private fun t(s: String): Instant = Instant.parse(s)

    private val topThree = listOf(
        row(1, 1, 7, 6120), row(1, 2, 34, 5875), row(1, 3, 14, 5310),
        row(2, 1, 25, 2275), row(2, 2, 2, 1890), row(2, 3, 30, 1640),
        row(3, 1, 32, 550), row(3, 2, 4, 275), row(3, 3, 9, 275),        // 4, 9 and 26 tie at 275: lowest ids win
        row(4, 1, 3, 129900), row(4, 2, 31, 75000), row(4, 3, 8, 54999),
        row(5, 1, 23, 99000), row(5, 2, 13, 64000), row(5, 3, 22, 52000),
        row(6, null, null, null),                                        // Paper Lantern Books: no payments
        row(7, 1, 33, 1720), row(7, 2, 12, 1450), row(7, 3, 21, 1325),
        row(8, null, null, null),                                        // Sunrise Grocers: no payments
    )

    @Test
    fun `top_payments_per_merchant returns three per merchant and keeps the empty ones`() = rollback {
        val rows = exercise(9, "top_payments_per_merchant")
        rows.assertColumns("merchant_id", "place", "payment_id", "amount_minor")
        rows.assertRowsInOrder(*topThree.toTypedArray())
    }

    @Test
    fun `top_payments_per_merchant follows new rows`() = rollback {
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES " +
                "(100, 4, 6, 1500, 'succeeded', '2026-06-10 12:00+00'), " +   // Paper Lantern's first sale
                "(101, 9, 3, 550, 'succeeded', '2026-06-11 08:00+00'), " +    // ties Metro's largest, higher id
                "(102, 12, 7, 9999, 'failed', '2026-06-12 12:00+00'), " +     // failed: not a sale
                "(103, 7, 4, 200000, 'pending', '2026-06-13 12:00+00')",      // pending: not a sale
        )
        val expected = topThree.toMutableList()
        expected[7] = row(3, 2, 101, 550)
        expected[8] = row(3, 3, 4, 275)
        expected[15] = row(6, 1, 100, 1500)
        exercise(9, "top_payments_per_merchant").assertRowsInOrder(*expected.toTypedArray())
    }

    private val latest = listOf(
        row(1, 24, t("2026-06-04T18:00:00Z"), true, "198.51.100.21"),
        row(2, 9, t("2026-03-01T00:00:00Z"), true, "198.51.100.40"),
        row(4, 3, t("2026-01-09T17:40:00Z"), true, "198.51.100.77"),
        row(5, 17, t("2026-03-06T19:58:00Z"), true, "192.0.2.15"),       // her own address, after the attack
        row(6, 18, t("2026-03-12T16:35:00Z"), true, "198.51.100.90"),
        row(9, 7, t("2026-01-21T08:55:00Z"), true, "192.0.2.60"),
        row(10, 27, t("2026-06-08T07:31:30Z"), true, "198.51.100.12"),
        row(12, 19, t("2026-03-01T09:10:00Z"), true, "192.0.2.88"),
        row(13, 23, t("2026-05-16T15:50:00Z"), true, "192.0.2.33"),
    )

    @Test
    fun `latest_login takes every column from the same row`() = rollback {
        val rows = exercise(9, "latest_login")
        rows.assertColumns("customer_id", "event_id", "occurred_at", "success", "ip")
        rows.assertRowsInOrder(*latest.toTypedArray())
    }

    @Test
    fun `latest_login follows new rows`() = rollback {
        update(
            "INSERT INTO login_events (event_id, customer_id, occurred_at, success, ip) VALUES " +
                "(100, 1, '2026-06-20 08:00:00+00', false, '203.0.113.50'), " +   // Asha's latest attempt fails
                "(101, 11, '2026-06-21 09:00:00+00', true, '192.0.2.99'), " +     // Kofi's first login
                "(102, 2, '2026-06-22 12:00:00+00', true, '198.51.100.40'), " +   // two attempts in the same
                "(103, 2, '2026-06-22 12:00:00+00', false, '203.0.113.51'), " +   // instant: 103 is the later one
                "(104, 13, '2026-01-01 07:00:00+00', false, '203.0.113.52')",     // newest id, oldest time
        )
        val expected = latest.toMutableList()
        expected[0] = row(1, 100, t("2026-06-20T08:00:00Z"), false, "203.0.113.50")
        expected[1] = row(2, 103, t("2026-06-22T12:00:00Z"), false, "203.0.113.51")
        expected.add(7, row(11, 101, t("2026-06-21T09:00:00Z"), true, "192.0.2.99"))
        exercise(9, "latest_login").assertRowsInOrder(*expected.toTypedArray())
    }

    @Test
    fun `payments_after_cursor returns the page after payment 18`() = rollback {
        val rows = exercise(9, "payments_after_cursor")
        rows.assertColumns("payment_id", "created_at", "amount_minor")
        rows.assertRowsInOrder(
            row(17, t("2026-03-12T16:40:00Z"), 18999),
            row(16, t("2026-03-08T19:20:00Z"), 31500),
            row(15, t("2026-03-06T20:00:00Z"), 89900),
            row(14, t("2026-03-04T09:30:00Z"), 5310),
            row(13, t("2026-03-01T00:00:00Z"), 64000),
        )
    }

    @Test
    fun `payments_after_cursor ignores new payments and keeps tied ones`() = rollback {
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES " +
                "(100, 1, 1, 1111, 'succeeded', '2026-07-01 10:00+00'), " +   // arrives while the user pages: page 1
                "(101, 2, 2, 2222, 'failed', '2026-03-12 16:42:10+00')",      // same instant as 18, larger id: before 18
        )
        // payment 17 recorded in the same instant as payment 18: smaller id, so it comes right after 18
        update("UPDATE payments SET created_at = '2026-03-12 16:42:10+00' WHERE payment_id = 17")
        exercise(9, "payments_after_cursor").assertRowsInOrder(
            row(17, t("2026-03-12T16:42:10Z"), 18999),
            row(16, t("2026-03-08T19:20:00Z"), 31500),
            row(15, t("2026-03-06T20:00:00Z"), 89900),
            row(14, t("2026-03-04T09:30:00Z"), 5310),
            row(13, t("2026-03-01T00:00:00Z"), 64000),
        )
    }
}
