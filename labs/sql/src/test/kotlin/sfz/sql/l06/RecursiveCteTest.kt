package sfz.sql.l06

import org.junit.jupiter.api.Test
import sfz.sql.support.rollback
import sfz.sql.support.row
import java.time.LocalDate

/**
 * Lesson sql-06. Your queries are in src/main/resources/sfz/sql/l06/. Each test runs in a
 * transaction that is rolled back, and every statement is cancelled after 10 seconds, so a
 * recursion that never stops fails its test instead of hanging the build.
 */
class RecursiveCteTest {

    // the seed's forest: 1 -> 3 -> 6, 1 -> 5 -> 10, 2 -> 4 -> 8 -> 13, 7 -> 12, and roots 9 and 11
    private val forest = listOf(
        row(1, 1, 0, listOf(1)),
        row(3, 1, 1, listOf(1, 3)),
        row(6, 1, 2, listOf(1, 3, 6)),
        row(5, 1, 1, listOf(1, 5)),
        row(10, 1, 2, listOf(1, 5, 10)),
        row(2, 2, 0, listOf(2)),
        row(4, 2, 1, listOf(2, 4)),
        row(8, 2, 2, listOf(2, 4, 8)),
        row(13, 2, 3, listOf(2, 4, 8, 13)),
        row(7, 7, 0, listOf(7)),
        row(12, 7, 1, listOf(7, 12)),
        row(9, 9, 0, listOf(9)),
        row(11, 11, 0, listOf(11)),
    )

    @Test
    fun `referral_tree walks every chain to the bottom`() = rollback {
        val rows = exercise(6, "referral_tree")
        rows.assertColumns("customer_id", "root_id", "depth", "path")
        rows.assertRowsInOrder(*forest.toTypedArray())
    }

    @Test
    fun `referral_tree follows new rows`() = rollback {
        // Mateo (depth 3) refers Nia, who refers Omar: the chain under Ben grows to depth 5
        update(
            "INSERT INTO customers (customer_id, email, full_name, country_code, referred_by, created_at) VALUES " +
                "(14, 'nia.okafor@example.com', 'Nia Okafor', 'US', 13, '2026-07-01 10:00+00'), " +
                "(15, 'omar.farouk@example.com', 'Omar Farouk', 'EG', 14, '2026-07-02 10:00+00'), " +
                "(16, 'priya.nair@example.com', 'Priya Nair', 'IN', 11, '2026-07-03 10:00+00')",
        )
        val expected = forest.toMutableList()
        expected.add(9, row(14, 2, 4, listOf(2, 4, 8, 13, 14)))
        expected.add(10, row(15, 2, 5, listOf(2, 4, 8, 13, 14, 15)))
        expected.add(row(16, 11, 1, listOf(11, 16)))
        exercise(6, "referral_tree").assertRowsInOrder(*expected.toTypedArray())
    }

    @Test
    fun `money_reach finds every account money from 106 can reach, despite the cycles`() = rollback {
        val rows = exercise(6, "money_reach")
        rows.assertColumns("account_id", "hops")
        rows.assertRowsInOrder(
            row(104, 2),   // 106 pays Volt (304), Volt refunds Daniel (104)
            row(113, 2),   // ... and Mateo (113)
            row(302, 3),   // Daniel pays Blue Fern (302): three edges away
            row(304, 1),
            row(307, 1),
        )
    }

    @Test
    fun `money_reach follows new rows`() = rollback {
        // Blue Fern (302) sends money to Lena (112), and Lena sends some on to Farid (106)
        update(
            "INSERT INTO ledger_entries (entry_id, journal_id, account_id, entry_type, amount_minor, created_at) VALUES " +
                "(500, 3001, 302, 'withdrawal', -500, '2026-07-01 10:00+00'), " +
                "(501, 3001, 112, 'deposit',     500, '2026-07-01 10:00+00'), " +
                "(502, 3002, 112, 'withdrawal', -200, '2026-07-02 10:00+00'), " +
                "(503, 3002, 106, 'deposit',     200, '2026-07-02 10:00+00')",
        )
        exercise(6, "money_reach").assertRowsInOrder(
            row(104, 2),
            row(112, 4),
            row(113, 2),
            row(302, 3),
            row(304, 1),
            row(307, 1),
        )
    }

    private fun march(volumes: Map<Int, Pair<Int, Int>>) = (1..31).map { d ->
        val (n, sum) = volumes[d] ?: (0 to 0)
        row(LocalDate.of(2026, 3, d), n, sum)
    }

    // succeeded March payments per day; 6 March has only a failed payment, 20 March a pending one
    private val seedMarch = mapOf(
        1 to (1 to 64000),
        4 to (1 to 5310),
        8 to (1 to 31500),
        12 to (2 to 37998),
        15 to (1 to 18999),
        25 to (1 to 1325),
        31 to (1 to 52000),    // payment 22 at 23:59:59.5
    )

    @Test
    fun `daily_volume_march has a row for every day of March`() = rollback {
        val rows = exercise(6, "daily_volume_march")
        rows.assertColumns("day", "payments", "volume_minor")
        rows.assertRowsInOrder(*march(seedMarch).toTypedArray())
    }

    @Test
    fun `daily_volume_march follows new rows`() = rollback {
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES " +
                "(100, 1, 1, 1111, 'succeeded', '2026-03-02 00:00+00'), " +   // the first instant of 2 March
                "(101, 1, 1, 2222, 'succeeded', '2026-03-02 23:59+00'), " +
                "(102, 1, 1, 3333, 'failed',    '2026-03-03 12:00+00'), " +   // failed: 3 March stays at 0
                "(103, 1, 1, 4444, 'succeeded', '2026-04-01 00:00+00')",      // April, not March
        )
        exercise(6, "daily_volume_march").assertRowsInOrder(
            *march(seedMarch + (2 to (2 to 3333))).toTypedArray(),
        )
    }
}
