package sfz.sql.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.sql.support.Tx
import sfz.sql.support.rollback
import sfz.sql.support.row

/**
 * Lesson sql-02. Your files are in src/main/resources/sfz/sql/l02/. Every test runs in a
 * transaction that is rolled back, so the card_limits table you create disappears afterwards.
 */
class SchemaDesignTest {

    @Test
    fun `mcc_description_conflicts finds the mcc with two descriptions`() = rollback {
        val rows = exercise("sql/l02", "mcc_description_conflicts")
        rows.assertColumns("mcc", "descriptions")
        // payment 18's row says "Electronic stores"; the other 5732 rows say "Electronics stores"
        rows.assertRowsInOrder(row("5732", 2))
    }

    @Test
    fun `mcc_description_conflicts follows new rows`() = rollback {
        update(
            """
            INSERT INTO payments_export (payment_id, mcc, mcc_description, amount_minor) VALUES
                (90, '5411', 'Grocery', 1000),             -- a second description for 5411
                (91, '5732', 'Electronics stores', 2000),  -- a repeat of an existing description
                (92, '4111', 'Commuter transport', 275)    -- a new mcc with one description
            """,
        )
        exercise("sql/l02", "mcc_description_conflicts").assertRowsInOrder(row("5411", 2), row("5732", 2))
    }

    private fun Tx.createCardLimits() = runExercise("sql/l02", "card_limits")

    private val insert = "INSERT INTO card_limits (card_id, valid_during, daily_limit_minor) VALUES (?, ?::tstzrange, ?)"

    @Test
    fun `card_limits has the three columns with the right types`() = rollback {
        createCardLimits()
        query(
            """
            SELECT attname::text AS column_name, format_type(atttypid, atttypmod) AS type
            FROM pg_attribute
            WHERE attrelid = 'card_limits'::regclass AND attnum > 0 AND NOT attisdropped
            ORDER BY attnum
            """,
        ).assertRowsInOrder(
            row("card_id", "bigint"),
            row("valid_during", "tstzrange"),
            row("daily_limit_minor", "bigint"),
        )
    }

    @Test
    fun `card_limits accepts back-to-back periods and the same period on two cards`() = rollback {
        createCardLimits()
        assertThat(sqlStateOf(insert, 1L, "[2026-01-01,2026-07-01)", 500_000L)).isNull()
        assertThat(sqlStateOf(insert, 1L, "[2026-07-01,)", 750_000L)).describedAs("[Jul, ...) starts where [Jan, Jul) ends").isNull()
        assertThat(sqlStateOf(insert, 2L, "[2026-01-01,2026-07-01)", 500_000L)).describedAs("another card").isNull()
    }

    @Test
    fun `card_limits rejects two limits in force at once for one card`() = rollback {
        createCardLimits()
        assertThat(sqlStateOf(insert, 1L, "[2026-01-01,2026-07-01)", 500_000L)).isNull()
        assertThat(sqlStateOf(insert, 1L, "[2026-06-01,2026-08-01)", 600_000L))
            .describedAs("June overlaps [Jan, Jul); expected an exclusion (23P01) or unique (23505) violation")
            .isIn("23P01", "23505")
        assertThat(sqlStateOf(insert, 1L, "[2026-03-01,2026-03-02)", 1_000L))
            .describedAs("one day inside [Jan, Jul)")
            .isIn("23P01", "23505")
    }

    @Test
    fun `card_limits rejects a card that does not exist`() = rollback {
        createCardLimits()
        assertThat(sqlStateOf(insert, 999L, "[2026-01-01,2026-07-01)", 500_000L))
            .describedAs("card 999 is not in cards; expected a foreign key violation (23503)")
            .isEqualTo("23503")
    }

    @Test
    fun `card_limits accepts 1 to 10000000 and rejects everything else`() = rollback {
        createCardLimits()
        assertThat(sqlStateOf(insert, 3L, "[2026-01-01,2026-02-01)", 0L)).describedAs("zero").isEqualTo("23514")
        assertThat(sqlStateOf(insert, 3L, "[2026-01-01,2026-02-01)", -500L)).describedAs("negative").isEqualTo("23514")
        assertThat(sqlStateOf(insert, 3L, "[2026-01-01,2026-02-01)", 10_000_001L)).describedAs("above 100,000.00").isEqualTo("23514")
        assertThat(sqlStateOf(insert, 3L, "[2026-01-01,2026-02-01)", 10_000_000L)).describedAs("exactly 100,000.00").isNull()
        assertThat(sqlStateOf(insert, 4L, "[2026-01-01,2026-02-01)", 1L)).describedAs("one cent").isNull()
    }

    @Test
    fun `card_limits rejects NULL in every column`() = rollback {
        createCardLimits()
        assertThat(sqlStateOf(insert, null, "[2026-01-01,2026-02-01)", 100L)).describedAs("NULL card_id").isEqualTo("23502")
        assertThat(sqlStateOf(insert, 5L, null, 100L)).describedAs("NULL valid_during").isEqualTo("23502")
        assertThat(sqlStateOf(insert, 5L, "[2026-01-01,2026-02-01)", null)).describedAs("NULL daily_limit_minor").isEqualTo("23502")
    }

    @Test
    fun `balance_drift is empty on the seed, where every cache is right`() = rollback {
        val rows = exercise("sql/l02", "balance_drift")
        rows.assertColumns("account_id", "cached", "ledger")
        rows.assertRowsInOrder()
    }

    @Test
    fun `balance_drift finds a missed posting and a balance with no ledger rows`() = rollback {
        // a deposit posted to the ledger without updating either cached balance
        update(
            """
            INSERT INTO ledger_entries (journal_id, account_id, entry_type, amount_minor, created_at) VALUES
                (3001, 103, 'deposit',  1000, '2026-07-01 09:00+00'),
                (3001, 900, 'deposit', -1000, '2026-07-01 09:00+00')
            """,
        )
        // account 112 has no ledger rows at all, so its balance must be 0
        update("UPDATE accounts SET balance_minor = 700 WHERE account_id = 112")
        exercise("sql/l02", "balance_drift").assertRowsInOrder(
            row(103, 9086, 10086),
            row(112, 700, 0),
            row(900, -860000, -861000),
        )
    }

    @Test
    fun `balance_drift leaves alone an empty account with a zero balance`() = rollback {
        update("INSERT INTO accounts (account_id, kind, customer_id, opened_at) VALUES (211, 'customer', 11, '2026-07-01 00:00+00')")
        exercise("sql/l02", "balance_drift").assertRowsInOrder()
    }
}
