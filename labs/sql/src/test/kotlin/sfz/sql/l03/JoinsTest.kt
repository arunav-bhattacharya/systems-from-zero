package sfz.sql.l03

import org.junit.jupiter.api.Test
import sfz.sql.support.rollback
import sfz.sql.support.row

/**
 * Lesson sql-03. Your queries are in src/main/resources/sfz/sql/l03/. Each test runs in a
 * transaction that is rolled back, so rows a test adds never reach the next test.
 */
class JoinsTest {

    @Test
    fun `never_referred_anyone returns the six customers nobody names as referrer`() = rollback {
        val rows = exercise(3, "never_referred_anyone")
        rows.assertColumns("customer_id", "full_name")
        // referred_by holds 1, 2, 3, 4, 5, 7, 8 and five NULLs
        rows.assertRowsInOrder(
            row(6, "Farid Haddad"),
            row(9, "Ivy Chen"),
            row(10, "Jonas Weber"),
            row(11, "Kofi Mensah"),
            row(12, "Lena Novak"),
            row(13, "Mateo Ruiz"),
        )
    }

    @Test
    fun `never_referred_anyone follows new rows`() = rollback {
        // Mateo refers a new customer, so he leaves the list and the newcomer joins it
        update(
            "INSERT INTO customers (customer_id, email, full_name, country_code, referred_by, created_at) " +
                "VALUES (14, 'nia.okafor@example.com', 'Nia Okafor', 'US', 13, '2026-07-01 10:00+00')",
        )
        exercise(3, "never_referred_anyone").assertRowsInOrder(
            row(6, "Farid Haddad"),
            row(9, "Ivy Chen"),
            row(10, "Jonas Weber"),
            row(11, "Kofi Mensah"),
            row(12, "Lena Novak"),
            row(14, "Nia Okafor"),
        )
    }

    @Test
    fun `merchant_failed_payments keeps merchants that have no failed payment`() = rollback {
        val rows = exercise(3, "merchant_failed_payments")
        rows.assertColumns("merchant_id", "name", "payment_id", "amount_minor")
        rows.assertRowsInOrder(
            row(1, "Northwind Grocers", null, null),     // only good payments
            row(2, "Blue Fern Cafe", 6, 2150),
            row(2, "Blue Fern Cafe", 10, 3400),
            row(2, "Blue Fern Cafe", 36, 2090),
            row(3, "Metro Transit", null, null),
            row(4, "Volt Electronics", 15, 89900),
            row(5, "Harbor Hotel", null, null),
            row(6, "Paper Lantern Books", null, null),   // no payments at all
            row(7, "Quick Bite", 27, 1980),
            row(8, "Sunrise Grocers", null, null),
        )
    }

    @Test
    fun `merchant_failed_payments follows new rows`() = rollback {
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) " +
                "VALUES (100, 1, 8, 999, 'failed', '2026-07-01 12:00+00')",
        )
        val rows = exercise(3, "merchant_failed_payments")
        rows.assertRowsInOrder(
            row(1, "Northwind Grocers", null, null),
            row(2, "Blue Fern Cafe", 6, 2150),
            row(2, "Blue Fern Cafe", 10, 3400),
            row(2, "Blue Fern Cafe", 36, 2090),
            row(3, "Metro Transit", null, null),
            row(4, "Volt Electronics", 15, 89900),
            row(5, "Harbor Hotel", null, null),
            row(6, "Paper Lantern Books", null, null),
            row(7, "Quick Bite", 27, 1980),
            row(8, "Sunrise Grocers", 100, 999),
        )
    }

    @Test
    fun `merchants_with_refunds lists each refunding merchant once`() = rollback {
        val rows = exercise(3, "merchants_with_refunds")
        rows.assertColumns("merchant_id", "name")
        // merchant 4 has three refunded payments and merchant 5 has two refunds on one payment
        rows.assertRowsInOrder(
            row(1, "Northwind Grocers"),
            row(4, "Volt Electronics"),
            row(5, "Harbor Hotel"),
        )
    }

    @Test
    fun `merchants_with_refunds follows new rows`() = rollback {
        update(
            "INSERT INTO refunds (refund_id, payment_id, amount_minor, reason, created_at) " +
                "VALUES (50, 2, 1890, 'customer_request', '2026-07-01 12:00+00')",   // payment 2 is at merchant 2
        )
        exercise(3, "merchants_with_refunds").assertRowsInOrder(
            row(1, "Northwind Grocers"),
            row(2, "Blue Fern Cafe"),
            row(4, "Volt Electronics"),
            row(5, "Harbor Hotel"),
        )
    }
}
