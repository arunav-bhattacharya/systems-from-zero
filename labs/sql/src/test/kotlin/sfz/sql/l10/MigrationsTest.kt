package sfz.sql.l10

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.flywaydb.core.Flyway
import org.flywaydb.core.api.exception.FlywayValidateException
import org.junit.jupiter.api.Test
import org.opentest4j.AssertionFailedError
import sfz.sql.support.CourseDb
import sfz.sql.support.Rows
import java.sql.Connection
import java.sql.SQLException
import java.util.concurrent.atomic.AtomicInteger

/**
 * Lesson sql-10. Your file is src/main/resources/sfz/sql/l10/db/migration/V2__payout_status.sql.
 *
 * Each test runs Flyway against a brand-new, empty schema in the test database, the way a
 * fresh environment or a CI run would, and drops the schema afterwards. Flyway reads the
 * migrations from the classpath folder sfz/sql/l10/db/migration.
 */
class MigrationsTest {

    private companion object {
        val next = AtomicInteger()
    }

    /** Runs [block] with a Flyway for a new, empty schema and a connection whose search_path is that schema. */
    private fun freshSchema(block: (schema: String, flyway: (target: String?) -> Flyway, conn: Connection) -> Unit) {
        val schema = "lab14_m${next.incrementAndGet()}_${ProcessHandle.current().pid()}"
        fun flyway(target: String?): Flyway = Flyway.configure()
            .dataSource(CourseDb.jdbcUrl, CourseDb.username, CourseDb.password)
            .schemas(schema)                                   // Flyway creates it, and keeps its history there
            .locations("classpath:sfz/sql/l10/db/migration")
            .apply { if (target != null) target(target) }
            .load()
        CourseDb.connect().use { conn ->
            try {
                block(schema, ::flyway, conn)
            } finally {
                conn.createStatement().use { it.execute("DROP SCHEMA IF EXISTS $schema CASCADE") }
            }
        }
    }

    private fun Connection.rows(sql: String): Rows = createStatement().use { st -> st.executeQuery(sql).use { Rows.from(it) } }

    private fun Connection.sqlStateOf(sql: String): String? = try {
        createStatement().use { it.execute(sql) }
        null
    } catch (e: SQLException) {
        e.sqlState
    }

    private fun migrateOrFail(flyway: Flyway) = try {
        flyway.migrate()
    } catch (e: Exception) {
        val cause = generateSequence(e as Throwable) { it.cause }.filterIsInstance<SQLException>().firstOrNull()
        throw AssertionFailedError("migrate failed" + (cause?.let { " with SQLSTATE ${it.sqlState}: ${it.message}" } ?: ": ${e.message}"), e)
    }

    @Test
    fun `migrate builds the payouts schema from nothing and records both versions`() = freshSchema { schema, flyway, conn ->
        val result = migrateOrFail(flyway(null))
        assertThat(result.migrationsExecuted).isEqualTo(2)
        conn.rows("SELECT version, description, success FROM $schema.flyway_schema_history WHERE version IS NOT NULL ORDER BY installed_rank")
            .assertRowsInOrder(listOf("1", "create payouts", true), listOf("2", "payout status", true))
    }

    @Test
    fun `a payout created without a status starts as pending, and an unknown status is refused`() = freshSchema { schema, flyway, conn ->
        migrateOrFail(flyway(null))
        val missing = conn.sqlStateOf("INSERT INTO $schema.payouts (merchant_id, amount_minor) VALUES (1, 5000)")
        assertThat(missing).describedAs("SQLSTATE of an insert that names no status (23502: status has no default)").isNull()
        conn.rows("SELECT merchant_id, amount_minor, status FROM $schema.payouts").assertRowsInOrder(listOf(1L, 5000L, "pending"))
        assertThat(conn.sqlStateOf("INSERT INTO $schema.payouts (merchant_id, amount_minor, status) VALUES (1, 5000, 'lost')"))
            .describedAs("a status outside pending, sent and failed").isEqualTo("23514")
        assertThat(conn.sqlStateOf("INSERT INTO $schema.payouts (merchant_id, amount_minor, status) VALUES (1, 5000, NULL)"))
            .describedAs("an explicit NULL status").isEqualTo("23502")
    }

    @Test
    fun `V2 also runs on a payouts table that already has rows, as in production`() = freshSchema { schema, flyway, conn ->
        migrateOrFail(flyway("1"))                             // production is at version 1 ...
        conn.createStatement().use {
            it.execute("INSERT INTO $schema.payouts (merchant_id, amount_minor) VALUES (1, 4800), (4, 120000), (5, 99000)")
        }                                                      // ... and payouts has rows
        val result = migrateOrFail(flyway(null))
        assertThat(result.migrationsExecuted).isEqualTo(1)
        conn.rows("SELECT merchant_id, status FROM $schema.payouts ORDER BY merchant_id")
            .assertRowsInOrder(listOf(1L, "pending"), listOf(4L, "pending"), listOf(5L, "pending"))
    }

    @Test
    fun `the sender's query for pending payouts has a partial index`() = freshSchema { schema, flyway, conn ->
        migrateOrFail(flyway(null))
        conn.rows("SELECT indexdef FROM pg_indexes WHERE schemaname = '$schema' AND indexname = 'payouts_pending_idx'")
            .assertRowsInOrder(listOf("CREATE INDEX payouts_pending_idx ON $schema.payouts USING btree (created_at) WHERE (status = 'pending'::text)"))
    }

    @Test
    fun `a second migrate finds nothing to do`() = freshSchema { _, flyway, _ ->
        migrateOrFail(flyway(null))
        assertThat(flyway(null).migrate().migrationsExecuted).isEqualTo(0)
    }

    @Test
    fun `an applied migration that was edited afterwards stops the next migrate`() = freshSchema { schema, flyway, conn ->
        migrateOrFail(flyway(null))
        // what editing V1__create_payouts.sql after it ran looks like to Flyway: a different checksum
        conn.createStatement().use { it.execute("UPDATE $schema.flyway_schema_history SET checksum = checksum + 1 WHERE version = '1'") }
        assertThat(flyway(null).validateWithResult().validationSuccessful).isFalse()
        assertThatThrownBy { flyway(null).migrate() }.isInstanceOf(FlywayValidateException::class.java)
    }
}
