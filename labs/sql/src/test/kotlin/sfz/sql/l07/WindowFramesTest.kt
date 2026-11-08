package sfz.sql.l07

import org.junit.jupiter.api.Test
import sfz.sql.support.rollback
import sfz.sql.support.row
import java.time.Instant
import java.time.LocalDate

/**
 * Lesson sql-07. Your queries are in src/main/resources/sfz/sql/l07/. Each test runs in a
 * transaction that is rolled back, so the rows a test adds are gone before the next one starts.
 */
class WindowFramesTest {

    private fun t(s: String): Instant = Instant.parse(s)

    // account 900 funds every deposit; four deposits share 2026-01-02 09:00, two share 01-10, two share 01-21
    private val clearing = listOf(
        row(2, t("2026-01-02T09:00:00Z"), -100000, -100000),
        row(4, t("2026-01-02T09:00:00Z"), -80000, -180000),
        row(6, t("2026-01-02T09:00:00Z"), -30000, -210000),
        row(8, t("2026-01-02T09:00:00Z"), -140000, -350000),
        row(16, t("2026-01-10T09:00:00Z"), -50000, -400000),
        row(18, t("2026-01-10T09:00:00Z"), -5000, -405000),
        row(24, t("2026-01-15T09:00:00Z"), -60000, -465000),
        row(26, t("2026-01-20T09:00:00Z"), -20000, -485000),
        row(30, t("2026-01-21T09:00:00Z"), -5000, -490000),
        row(32, t("2026-01-21T09:00:00Z"), -5000, -495000),
        row(36, t("2026-02-01T09:00:00Z"), -75000, -570000),
        row(40, t("2026-02-03T09:00:00Z"), -90000, -660000),
        row(66, t("2026-03-18T14:00:00Z"), -80000, -740000),
        row(70, t("2026-03-30T09:00:00Z"), -50000, -790000),
        row(84, t("2026-04-15T09:00:00Z"), -20000, -810000),
        row(100, t("2026-06-01T09:00:00Z"), -50000, -860000),   // equals accounts.balance_minor for 900
    )

    @Test
    fun `clearing_statement adds tied entries one at a time`() = rollback {
        val rows = exercise("sql/l07", "clearing_statement")
        rows.assertColumns("entry_id", "created_at", "amount_minor", "balance_minor")
        rows.assertRowsInOrder(*clearing.toTypedArray())
    }

    @Test
    fun `clearing_statement follows new rows`() = rollback {
        // three more deposits in one batch at 17:00, inserted in reverse entry_id order
        update(
            "INSERT INTO ledger_entries (entry_id, journal_id, account_id, entry_type, amount_minor, created_at) VALUES " +
                "(504, 3003, 105, 'deposit', 30000, '2026-06-30 17:00+00'), (505, 3003, 900, 'deposit', -30000, '2026-06-30 17:00+00'), " +
                "(502, 3002, 103, 'deposit', 20000, '2026-06-30 17:00+00'), (503, 3002, 900, 'deposit', -20000, '2026-06-30 17:00+00'), " +
                "(500, 3001, 101, 'deposit', 10000, '2026-06-30 17:00+00'), (501, 3001, 900, 'deposit', -10000, '2026-06-30 17:00+00')",
        )
        exercise("sql/l07", "clearing_statement").assertRowsInOrder(
            *clearing.toTypedArray(),
            row(501, t("2026-06-30T17:00:00Z"), -10000, -870000),
            row(503, t("2026-06-30T17:00:00Z"), -20000, -890000),
            row(505, t("2026-06-30T17:00:00Z"), -30000, -920000),
        )
    }

    private fun d(day: Int) = LocalDate.of(2026, 3, day)

    @Test
    fun `seven_day_volume measures the frame in days, not rows`() = rollback {
        val rows = exercise("sql/l07", "seven_day_volume")
        rows.assertColumns("day", "volume_minor", "volume_7d_minor")
        rows.assertRowsInOrder(
            row(d(1), 64000, 64000),
            row(d(4), 5310, 69310),
            row(d(8), 31500, 36810),     // 2 to 8 March: the 4th and the 8th
            row(d(12), 37998, 69498),
            row(d(15), 18999, 56997),
            row(d(25), 1325, 1325),      // nothing else between 19 and 25 March
            row(d(31), 52000, 53325),
        )
    }

    @Test
    fun `seven_day_volume follows new rows`() = rollback {
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES " +
                "(100, 1, 1, 1000, 'succeeded', '2026-02-27 10:00+00'), " +    // February: inside 1 and 4 March's 7 days
                "(101, 2, 2, 2000, 'succeeded', '2026-03-02 10:00+00'), " +    // a new March day
                "(102, 9, 3, 5000, 'failed', '2026-03-26 10:00+00'), " +       // failed: no row for 26 March
                "(103, 1, 1, 7000, 'succeeded', '2026-04-01 00:00+00'), " +    // April
                "(104, 1, 1, 3000, 'succeeded', '2026-02-22 23:59:59+00')",    // 7 days and 1 second before 1 March
        )
        exercise("sql/l07", "seven_day_volume").assertRowsInOrder(
            row(d(1), 64000, 65000),
            row(d(2), 2000, 67000),
            row(d(4), 5310, 72310),
            row(d(8), 31500, 38810),
            row(d(12), 37998, 69498),
            row(d(15), 18999, 56997),
            row(d(25), 1325, 1325),
            row(d(31), 52000, 53325),
        )
    }

    @Test
    fun `failed_login_streaks counts failures in a row, not in total`() = rollback {
        val rows = exercise("sql/l07", "failed_login_streaks")
        rows.assertColumns("customer_id", "failures", "first_at", "last_at")
        rows.assertRowsInOrder(
            row(5, 6, t("2026-03-06T19:52:00Z"), t("2026-03-06T19:53:40Z")),   // Elena, from 203.0.113.7
        )
    }

    @Test
    fun `failed_login_streaks follows new rows`() = rollback {
        update(
            "INSERT INTO login_events (event_id, customer_id, occurred_at, success, ip) VALUES " +
                // Elena again: three failures and no success after them (a run at the end still counts)
                "(100, 5, '2026-06-20 09:00:00+00', false, '203.0.113.9'), " +
                "(101, 5, '2026-06-20 09:00:30+00', false, '203.0.113.9'), " +
                "(102, 5, '2026-06-20 09:01:00+00', false, '203.0.113.9'), " +
                // Ben: two failures, a success, two failures: four in total, never three in a row
                "(103, 2, '2026-05-10 08:00:00+00', false, '198.51.100.40'), " +
                "(104, 2, '2026-05-10 08:00:20+00', false, '198.51.100.40'), " +
                "(105, 2, '2026-05-10 08:00:40+00', true,  '198.51.100.40'), " +
                "(106, 2, '2026-05-10 09:00:00+00', false, '198.51.100.40'), " +
                "(107, 2, '2026-05-10 09:00:20+00', false, '198.51.100.40'), " +
                // Mateo: three failures; Lena's success in between is another customer's login
                "(108, 13, '2026-06-01 10:00:00+00', false, '192.0.2.33'), " +
                "(109, 13, '2026-06-01 10:01:00+00', false, '192.0.2.33'), " +
                "(110, 12, '2026-06-01 10:01:30+00', true,  '192.0.2.88'), " +
                "(111, 13, '2026-06-01 10:02:00+00', false, '192.0.2.33')",
        )
        exercise("sql/l07", "failed_login_streaks").assertRowsInOrder(
            row(5, 6, t("2026-03-06T19:52:00Z"), t("2026-03-06T19:53:40Z")),
            row(5, 3, t("2026-06-20T09:00:00Z"), t("2026-06-20T09:01:00Z")),
            row(13, 3, t("2026-06-01T10:00:00Z"), t("2026-06-01T10:02:00Z")),
        )
    }
}
