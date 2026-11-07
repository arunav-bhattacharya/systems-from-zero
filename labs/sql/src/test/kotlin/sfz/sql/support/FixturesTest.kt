package sfz.sql.support

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import java.io.File

/**
 * Guards the track's fixtures. Every lesson's tests and Try-its assume these facts, so a change
 * to seed.sql that breaks one of them should fail here first, with a clear message.
 */
class SeedFilesInSyncTest {

    // Gradle runs tests with labs/sql as the working directory
    private val copies = File("../env/postgres/course")

    @Test
    fun `the Compose service loads exact copies of the test fixtures`() {
        for (name in listOf("schema.sql", "seed.sql")) {
            val file = File(copies, name)
            assertThat(file).describedAs("env/postgres/course/$name").exists()
            assertThat(file.readText())
                .describedAs("env/postgres/course/$name must equal sfz/sql/support/$name; copy it over after editing")
                .isEqualTo(CourseDb.resource("sfz/sql/support/$name"))
        }
    }
}

class SeedInvariantsTest {

    @Test
    fun `the seed has the documented number of rows`() = rollback {
        query(
            """
            SELECT (SELECT count(*) FROM customers)       AS customers,
                   (SELECT count(*) FROM accounts)        AS accounts,
                   (SELECT count(*) FROM cards)           AS cards,
                   (SELECT count(*) FROM merchants)       AS merchants,
                   (SELECT count(*) FROM payments)        AS payments,
                   (SELECT count(*) FROM refunds)         AS refunds,
                   (SELECT count(*) FROM ledger_entries)  AS ledger_entries,
                   (SELECT count(*) FROM payments_export) AS payments_export,
                   (SELECT count(*) FROM login_events)    AS login_events,
                   (SELECT count(*) FROM jobs)            AS jobs
            """,
        ).assertRowsInOrder(row(13, 23, 14, 8, 37, 6, 104, 10, 27, 8))
    }

    @Test
    fun `every journal in the ledger sums to zero`() = rollback {
        query("SELECT journal_id FROM ledger_entries GROUP BY journal_id HAVING sum(amount_minor) <> 0")
            .assertRowsInOrder()
    }

    @Test
    fun `every cached balance equals its ledger`() = rollback {
        query(
            """
            SELECT a.account_id
            FROM accounts a
            LEFT JOIN (SELECT account_id, sum(amount_minor) AS total FROM ledger_entries GROUP BY account_id) s
                   ON s.account_id = a.account_id
            WHERE a.balance_minor <> coalesce(s.total, 0)
            """,
        ).assertRowsInOrder()
    }

    @Test
    fun `payment statuses split 30, 5 and 2`() = rollback {
        query("SELECT status, count(*) FROM payments GROUP BY status ORDER BY status")
            .assertRowsInOrder(row("failed", 5), row("pending", 2), row("succeeded", 30))
    }
}
