package sfz.sql.l06

import org.junit.jupiter.api.Test
import sfz.sql.support.rollback
import sfz.sql.support.row
import java.time.LocalDate

/**
 * Lesson sql-06. Your queries are in src/main/resources/sfz/sql/l06/. Each test runs in a
 * transaction that is rolled back, so the rows a test adds are gone before the next one starts.
 */
class WindowFunctionsTest {

    // the ten largest succeeded payments, then the three-way tie at 18999 sharing 11th place
    private val topTen = listOf(
        row(1, 3, 129900),
        row(2, 23, 99000),
        row(3, 31, 75000),
        row(4, 13, 64000),
        row(5, 8, 54999),
        row(6, 22, 52000),
        row(7, 5, 48000),
        row(8, 35, 41000),
        row(9, 16, 31500),
        row(10, 28, 23450),
    )

    @Test
    fun `payment_places lets tied payments share a place`() = rollback {
        val rows = exercise("sql/l06", "payment_places")
        rows.assertColumns("place", "payment_id", "amount_minor")
        rows.assertRowsInOrder(
            *topTen.toTypedArray(),
            row(11, 17, 18999),
            row(11, 18, 18999),
            row(11, 19, 18999),   // 13 rows: nobody is 12th, the next payment (6120) is 14th
        )
    }

    @Test
    fun `payment_places follows new rows`() = rollback {
        // a second 990.00 ties payment 23 for 2nd place, so 3rd place disappears;
        // a failed 5000.00 must not place at all
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES " +
                "(100, 12, 5, 99000, 'succeeded', '2026-06-20 10:00+00'), " +
                "(101, 7, 4, 500000, 'failed', '2026-06-21 10:00+00')",
        )
        exercise("sql/l06", "payment_places").assertRowsInOrder(
            row(1, 3, 129900),
            row(2, 23, 99000),
            row(2, 100, 99000),
            row(4, 31, 75000),
            row(5, 13, 64000),
            row(6, 8, 54999),
            row(7, 22, 52000),
            row(8, 5, 48000),
            row(9, 35, 41000),
            row(10, 16, 31500),
            row(11, 28, 23450),
            row(12, 17, 18999),
            row(12, 18, 18999),
            row(12, 19, 18999),
        )
    }

    @Test
    fun `duplicate_charges finds the one double charge`() = rollback {
        val rows = exercise("sql/l06", "duplicate_charges")
        rows.assertColumns("payment_id", "duplicate_of", "seconds_after")
        rows.assertRowsInOrder(row(18, 17, 130))   // Farid, Volt Electronics, 189.99 twice, 2 min 10 s apart
    }

    @Test
    fun `duplicate_charges follows new rows`() = rollback {
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES " +
                "(100, 1, 1, 5875, 'succeeded', '2026-06-04 18:09:00+00'), " +   // 4 min after payment 34: a duplicate
                "(101, 1, 1, 5875, 'succeeded', '2026-06-04 18:15:00+00'), " +   // 6 min after 100: too late to count
                "(102, 9, 3, 275, 'succeeded', '2026-02-10 08:02:00+00'), " +    // Grace's ride repeated after 1 min
                "(103, 2, 3, 275, 'succeeded', '2026-02-10 08:01:30+00'), " +    // Ben's own ride: another card
                "(104, 8, 4, 18999, 'failed', '2026-03-12 16:41:00+00')",        // a failed try between 17 and 18
        )
        exercise("sql/l06", "duplicate_charges").assertRowsInOrder(
            row(18, 17, 130),
            row(100, 34, 240),
            row(102, 9, 60),
        )
    }

    private fun m(month: Int) = LocalDate.of(2026, month, 1)

    private val seedVolumes = listOf(
        row(1, m(1), 4250, 4250),
        row(1, m(2), 8620, 12870),
        row(1, m(3), 5310, 18180),
        row(1, m(4), 3880, 22060),
        row(1, m(5), 4999, 27059),
        row(1, m(6), 5875, 32934),
        row(2, m(1), 1890, 1890),
        row(2, m(4), 2275, 4165),
        row(2, m(5), 1640, 5805),
        row(3, m(1), 275, 275),
        row(3, m(2), 275, 550),
        row(3, m(4), 275, 825),
        row(3, m(5), 550, 1375),
        row(4, m(1), 129900, 129900),
        row(4, m(2), 54999, 184899),
        row(4, m(3), 56997, 241896),
        row(4, m(4), 23450, 265346),
        row(4, m(5), 75000, 340346),
        row(5, m(1), 48000, 48000),
        row(5, m(3), 147500, 195500),
        row(5, m(4), 99000, 294500),
        row(5, m(6), 41000, 335500),
        row(7, m(2), 1450, 1450),
        row(7, m(3), 1325, 2775),
        row(7, m(5), 1720, 4495),
    )

    @Test
    fun `merchant_running_volume restarts the running total for every merchant`() = rollback {
        val rows = exercise("sql/l06", "merchant_running_volume")
        rows.assertColumns("merchant_id", "month", "volume_minor", "running_volume_minor")
        rows.assertRowsInOrder(*seedVolumes.toTypedArray())
    }

    @Test
    fun `merchant_running_volume follows new rows`() = rollback {
        update(
            "INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES " +
                "(100, 4, 6, 3000, 'succeeded', '2026-06-10 12:00+00'), " +   // Paper Lantern's first sale
                "(101, 1, 1, 1000, 'succeeded', '2026-02-28 23:59:59+00'), " + // the last second of February
                "(102, 2, 2, 7777, 'failed', '2026-06-15 12:00+00'), " +       // failed: no June row for Blue Fern
                "(103, 9, 7, 2000, 'succeeded', '2026-06-30 23:59:59+00'), " +
                "(104, 9, 7, 4000, 'succeeded', '2026-07-01 00:00+00')",       // July has its own row
        )
        val expected = seedVolumes.toMutableList()
        // merchant 1: February grows by 1000, and every later month carries it
        expected[1] = row(1, m(2), 9620, 13870)
        expected[2] = row(1, m(3), 5310, 19180)
        expected[3] = row(1, m(4), 3880, 23060)
        expected[4] = row(1, m(5), 4999, 28059)
        expected[5] = row(1, m(6), 5875, 33934)
        expected.add(22, row(6, m(6), 3000, 3000))
        expected.add(row(7, m(6), 2000, 6495))
        expected.add(row(7, m(7), 4000, 10495))
        exercise("sql/l06", "merchant_running_volume").assertRowsInOrder(*expected.toTypedArray())
    }
}
