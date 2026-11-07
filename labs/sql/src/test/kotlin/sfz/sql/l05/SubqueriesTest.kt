package sfz.sql.l05

import org.junit.jupiter.api.Test
import sfz.sql.support.rollback
import sfz.sql.support.row

/**
 * Lesson sql-05. Your queries are in src/main/resources/sfz/sql/l05/. Each test runs in a
 * transaction that is rolled back, so rows a test adds never reach the next test.
 */
class SubqueriesTest {

    @Test
    fun `above_merchant_average compares each payment with its own merchant`() = rollback {
        val rows = exercise(5, "above_merchant_average")
        rows.assertColumns("payment_id", "merchant_id", "amount_minor", "merchant_avg")
        // averages: m1 4704.86, m2 1935, m3 343.75, m4 48620.86, m5 55916.67, m7 1498.33
        rows.assertRowsInOrder(
            row(3, 4, 129900, 48621),
            row(7, 1, 6120, 4705),
            row(8, 4, 54999, 48621),
            row(13, 5, 64000, 55917),
            row(14, 1, 5310, 4705),
            row(23, 5, 99000, 55917),
            row(25, 2, 2275, 1935),
            row(29, 1, 4999, 4705),
            row(31, 4, 75000, 48621),
            row(32, 3, 550, 344),       // far below the overall average of 24015, far above Metro's
            row(33, 7, 1720, 1498),
            row(34, 1, 5875, 4705),
        )
    }

    @Test
    fun `above_merchant_average follows new rows`() = rollback {
        // a 50.00 ride at Metro Transit lifts its average to 1275, so payment 32 (5.50) drops out
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) " +
                "VALUES (100, 9, 3, 5000, 'succeeded', '2026-06-01 08:00+00')",
        )
        exercise(5, "above_merchant_average").assertRowsInOrder(
            row(3, 4, 129900, 48621),
            row(7, 1, 6120, 4705),
            row(8, 4, 54999, 48621),
            row(13, 5, 64000, 55917),
            row(14, 1, 5310, 4705),
            row(23, 5, 99000, 55917),
            row(25, 2, 2275, 1935),
            row(29, 1, 4999, 4705),
            row(31, 4, 75000, 48621),
            row(33, 7, 1720, 1498),
            row(34, 1, 5875, 4705),
            row(100, 3, 5000, 1275),
        )
    }

    @Test
    fun `above_average_spenders averages over customers`() = rollback {
        val rows = exercise(5, "above_average_spenders")
        rows.assertColumns("customer_id", "full_name", "spend_minor")
        // nine customers spent 720455 in total: the average customer spends 80050.56
        rows.assertRowsInOrder(
            row(1, "Asha Rao", 120555),
            row(2, "Ben Carter", 170768),
            row(4, "Daniel Kim", 133625),
            row(10, "Jonas Weber", 86000),
        )
    }

    @Test
    fun `above_average_spenders follows new rows`() = rollback {
        // Grace (card 9) books a 3,000.00 hotel stay: the average customer now spends 113383.89
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) " +
                "VALUES (100, 9, 5, 300000, 'succeeded', '2026-06-20 18:00+00')",
        )
        exercise(5, "above_average_spenders").assertRowsInOrder(
            row(1, "Asha Rao", 120555),
            row(2, "Ben Carter", 170768),
            row(4, "Daniel Kim", 133625),
            row(7, "Grace Lee", 301100),
        )
    }

    @Test
    fun `monthly_active_customers counts customers, not payments`() = rollback {
        val rows = exercise(5, "monthly_active_customers")
        rows.assertColumns("month", "active_customers", "new_customers", "returning_customers")
        rows.assertRowsInOrder(
            row("2026-01", 5, 5, 0),
            row("2026-02", 5, 2, 3),    // Grace and Jonas pay for the first time
            row("2026-03", 6, 2, 4),    // eight payments, six customers; Farid's January payment failed
            row("2026-04", 5, 0, 5),
            row("2026-05", 5, 0, 5),
            row("2026-06", 2, 0, 2),
        )
    }

    @Test
    fun `monthly_active_customers follows new rows`() = rollback {
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES " +
                "(100, 11, 2, 1200, 'succeeded', '2026-06-21 09:00+00'), " +   // Ivy's first payment
                "(101, 11, 2, 800,  'succeeded', '2026-06-22 09:00+00'), " +   // and her second, same month
                "(102, 10, 2, 900,  'failed',    '2026-06-23 09:00+00'), " +   // Hugo fails again: not active
                "(103, 1,  1, 700,  'succeeded', '2026-06-24 09:00+00')",      // Asha, already active in June
        )
        exercise(5, "monthly_active_customers").assertRowsInOrder(
            row("2026-01", 5, 5, 0),
            row("2026-02", 5, 2, 3),
            row("2026-03", 6, 2, 4),
            row("2026-04", 5, 0, 5),
            row("2026-05", 5, 0, 5),
            row("2026-06", 3, 1, 2),
        )
    }
}
