package sfz.sql.l10

import com.zaxxer.hikari.HikariDataSource
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import org.opentest4j.AssertionFailedError
import sfz.sql.support.CourseDb
import sfz.sql.support.RoundTripCounter
import sfz.sql.support.resetStatements
import sfz.sql.support.rollback
import sfz.sql.support.roundTrips
import sfz.sql.support.row
import sfz.sql.support.statementsRun
import java.sql.Connection
import java.sql.SQLException
import java.sql.SQLTransientConnectionException
import java.time.Instant

/**
 * Lesson sql-10. Your files are in src/main/kotlin/sfz/sql/l10/ and
 * src/main/resources/sfz/sql/l10/db/migration/ (MigrationsTest checks the migration).
 *
 * The tests measure what a stopwatch can't measure reliably on a busy laptop: round trips
 * between the driver and the server (a counting socket, see support/RoundTrips.kt) and
 * statements the server ran (pg_stat_statements). Every test runs in a transaction that is
 * rolled back, so the seed stays as it was.
 */
class JdbcTest {

    // ---------------------------------------------------------------- MerchantRepository

    @Test
    fun `create returns the new merchant's id, and findByName finds it`() = rollback {
        val repo = MerchantRepository(conn)
        val id = repo.create("Copper Kettle", "5812", "IE")
        assertThat(id).describedAs("the identity column continues after the seed's 8 merchants").isGreaterThan(8L)
        assertThat(repo.findByName("Copper Kettle")).containsExactly(Merchant(id, "Copper Kettle", "5812", "IE"))
    }

    @Test
    fun `create stores a name with an apostrophe exactly as given`() = rollback {
        val repo = MerchantRepository(conn)
        val id = createOrFail { repo.create("Mama's Kitchen", "5812", "US") }
        query("SELECT name FROM merchants WHERE merchant_id = ?", id).assertRowsInOrder(row("Mama's Kitchen"))
    }

    @Test
    fun `an injection attempt in create is stored as data and runs nothing`() = rollback {
        val attack = "Evil Corp', '5999', 'GB') RETURNING merchant_id; UPDATE merchants SET name = 'pwned' WHERE merchant_id = 1; --"
        val repo = MerchantRepository(conn)
        val id = createOrFail { repo.create(attack, "5411", "US") }
        query("SELECT name, mcc, country_code FROM merchants WHERE merchant_id = ?", id)
            .assertRowsInOrder(row(attack, "5411", "US"))
        query("SELECT name FROM merchants WHERE merchant_id = 1").assertRowsInOrder(row("Northwind Grocers"))
    }

    @Test
    fun `findByName treats an injection string as a name, so it matches nothing`() = rollback {
        val found = MerchantRepository(conn).findByName("' OR '1'='1")
        assertThat(found).describedAs("no merchant is called ' OR '1'='1").isEmpty()
    }

    @Test
    fun `findByName finds a merchant whose name has an apostrophe`() = rollback {
        update("INSERT INTO merchants (merchant_id, name, mcc, country_code) VALUES (90, 'O''Brien''s Deli', '5814', 'IE')")
        val found = try {
            MerchantRepository(conn).findByName("O'Brien's Deli")
        } catch (e: SQLException) {
            throw AssertionFailedError("findByName(\"O'Brien's Deli\") failed with SQLSTATE ${e.sqlState}: ${e.message}", e)
        }
        assertThat(found).containsExactly(Merchant(90, "O'Brien's Deli", "5814", "IE"))
    }

    private fun createOrFail(block: () -> Long): Long = try {
        block()
    } catch (e: SQLException) {
        throw AssertionFailedError("create failed with SQLSTATE ${e.sqlState}: ${e.message}\nThe name became part of the SQL text.", e)
    }

    // ---------------------------------------------------------------- poolConfig

    @Test
    fun `the pool lends at most four connections, and a fifth borrower gives up after two seconds`() {
        HikariDataSource(poolConfig(CourseDb.jdbcUrl, CourseDb.username, CourseDb.password)).use { pool ->
            assertThat(pool.poolName).isEqualTo("importer")
            val held = mutableListOf<Connection>()
            try {
                repeat(4) { held += pool.connection }
                val started = System.nanoTime()
                val fifth = try {
                    pool.connection
                } catch (e: SQLTransientConnectionException) {
                    null
                }
                val waitedMs = (System.nanoTime() - started) / 1_000_000
                if (fifth != null) {
                    fifth.close()
                    throw AssertionFailedError("the pool lent a fifth connection; maximumPoolSize should be 4")
                }
                assertThat(waitedMs).describedAs("ms the fifth borrower waited (connectionTimeout 2 s)").isBetween(1_500L, 6_000L)
            } finally {
                held.forEach { it.close() }
            }
        }
    }

    // ---------------------------------------------------------------- insertPayments

    private fun payments(n: Int, merchantId: Long = 3, cardId: Long = 4): List<NewPayment> =
        (1..n).map { i ->
            NewPayment(cardId, merchantId, 100L + i, if (i % 10 == 0) "failed" else "succeeded", Instant.parse("2026-07-01T00:00:00Z").plusSeconds(i * 60L))
        }

    @Test
    fun `insertPayments stores every payment and returns the count`() = roundTrips {
        val rows = payments(1000)
        val inserted = insertPayments(conn, rows)
        assertThat(inserted).isEqualTo(1000)
        tx.query("SELECT count(*), sum(amount_minor), count(*) FILTER (WHERE status = 'failed') FROM payments WHERE created_at >= '2026-07-01'")
            .assertRowsInOrder(row(1000, rows.sumOf { it.amountMinor }, 100))
    }

    @Test
    fun `insertPayments sends 1,000 payments in a handful of round trips`() = roundTrips {
        val trips = count { insertPayments(conn, payments(1000)) }
        assertThat(trips).describedAs("round trips for 1,000 payments (one per payment means a loop of executeUpdate)").isLessThanOrEqualTo(10)
    }

    @Test
    fun `insertPayments stays at a handful of round trips for a new merchant's 2,500 payments`() = roundTrips {
        tx.update("INSERT INTO merchants (merchant_id, name, mcc, country_code) VALUES (91, 'Lakeside Fuel', '5999', 'CA')")
        val trips = count { assertThat(insertPayments(conn, payments(2500, merchantId = 91, cardId = 9))).isEqualTo(2500) }
        assertThat(trips).describedAs("round trips for 2,500 payments").isLessThanOrEqualTo(20)
        tx.query("SELECT count(*) FROM payments WHERE merchant_id = 91").assertRowsInOrder(row(2500))
    }

    @Test
    fun `through the importer pool, 1,000 payments run as at most 20 INSERT statements`() {
        val config = poolConfig(CourseDb.jdbcUrl, CourseDb.username, CourseDb.password)
        HikariDataSource(config).use { pool ->
            pool.connection.use { conn ->
                conn.autoCommit = false
                try {
                    resetStatements()
                    val inserted = insertPayments(conn, payments(1000))
                    assertThat(inserted).describedAs("insertPayments must return the number of rows, also when the driver rewrites the batch").isEqualTo(1000)
                    val statements = statementsRun("INSERT INTO payments")
                    assertThat(statements)
                        .describedAs("INSERT statements the server ran for 1,000 rows (1,000 means each row was its own INSERT)")
                        .isLessThanOrEqualTo(20)
                } finally {
                    conn.rollback()
                }
            }
        }
    }

    // ---------------------------------------------------------------- latestPayments

    private val seedLatest = listOf(
        LatestPayment(1, "Northwind Grocers", 34, 5875, Instant.parse("2026-06-04T18:05:00Z")),
        LatestPayment(2, "Blue Fern Cafe", 30, 1640, Instant.parse("2026-05-09T08:20:00Z")),
        LatestPayment(3, "Metro Transit", 32, 550, Instant.parse("2026-05-21T07:45:00Z")),
        LatestPayment(4, "Volt Electronics", 31, 75000, Instant.parse("2026-05-16T15:55:00Z")),
        LatestPayment(5, "Harbor Hotel", 35, 41000, Instant.parse("2026-06-12T21:30:00Z")),
        LatestPayment(6, "Paper Lantern Books", null, null, null),
        LatestPayment(7, "Quick Bite", 33, 1720, Instant.parse("2026-05-28T12:40:00Z")),
        LatestPayment(8, "Sunrise Grocers", null, null, null),
    )

    @Test
    fun `latestPayments lists every merchant with its latest succeeded payment`() = roundTrips {
        assertThat(latestPayments(conn)).containsExactlyElementsOf(seedLatest)
    }

    @Test
    fun `latestPayments reads the dashboard in at most two round trips`() = roundTrips {
        val trips = count { latestPayments(conn) }
        assertThat(trips).describedAs("round trips for 8 merchants (9 means one query per merchant: N+1)").isLessThanOrEqualTo(2)
    }

    @Test
    fun `latestPayments stays at two round trips with 40 more merchants`() = roundTrips {
        tx.update(
            """
            INSERT INTO merchants (merchant_id, name, mcc, country_code)
            SELECT 100 + g, 'Stall ' || g, '5814', 'US' FROM generate_series(1, 40) AS g
            """,
        )
        // stall g gets g payments; its latest is the last one, and the tie on created_at breaks by id
        tx.update(
            """
            INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at)
            SELECT 1000 + g * 100 + k, 4, 100 + g, 1000 * g + k, 'succeeded', timestamptz '2026-07-01 00:00+00' + g * interval '1 hour'
            FROM generate_series(1, 40) AS g, generate_series(1, g) AS k
            """,
        )
        var result: List<LatestPayment> = emptyList()
        val trips = count { result = latestPayments(conn) }
        assertThat(result).hasSize(48)
        assertThat(result.take(8)).containsExactlyElementsOf(seedLatest)
        assertThat(result.last()).isEqualTo(LatestPayment(140, "Stall 40", 1000 + 40 * 100 + 40L, 40040, Instant.parse("2026-07-02T16:00:00Z")))
        assertThat(trips).describedAs("round trips for 48 merchants (49 means N+1)").isLessThanOrEqualTo(2)
    }

    @Test
    fun `the round-trip counter itself counts one per query`() = roundTrips {
        // a guard for the measuring tool, not for your code
        val trips = count { tx.query("SELECT 1") }
        assertThat(trips).isEqualTo(1)
        assertThat(RoundTripCounter.PROPERTY).isNotBlank()
    }
}
