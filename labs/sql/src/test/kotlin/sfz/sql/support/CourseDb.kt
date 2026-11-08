package sfz.sql.support

import org.testcontainers.postgresql.PostgreSQLContainer
import java.sql.Connection
import java.sql.DriverManager

/**
 * One PostgreSQL 18 container for the whole test JVM, started on first use and loaded once with
 * the course schema and the small seed (`sfz/sql/support/schema.sql` and `seed.sql`).
 *
 * Tests never commit: [rollback] wraps every exercise in a transaction that is rolled back, so
 * the seed is the same for every test. Testcontainers removes the container when the JVM exits.
 */
object CourseDb {
    private val container: PostgreSQLContainer by lazy {
        PostgreSQLContainer("postgres:18")
            .withDatabaseName("sfz")
            .withUsername("sfz")
            .withPassword("sfz")
            // small and fast: the data is tiny, and losing it on a crash costs nothing
            .withCommand(
                "postgres",
                "-c", "fsync=off",
                "-c", "synchronous_commit=off",
                "-c", "full_page_writes=off",
                "-c", "shared_buffers=32MB",
                "-c", "max_connections=20",
                "-c", "timezone=UTC",
                // sql-10 counts the statements the server ran
                "-c", "shared_preload_libraries=pg_stat_statements",
            )
            .also { it.start() }
            .also { load(it) }
    }

    /** The JDBC URL, user and password of the seeded database, for a pool or Flyway (sql-10). */
    val jdbcUrl: String get() = container.jdbcUrl
    val username: String get() = container.username
    val password: String get() = container.password

    /** A new connection to the seeded database. The session time zone is UTC, as in the Try-its. */
    fun connect(): Connection {
        val c = container
        val conn = DriverManager.getConnection(c.jdbcUrl, c.username, c.password)
        // pgJDBC sends the JVM's time zone at login; pin UTC so '2026-03-01' means the same everywhere
        conn.createStatement().use { it.execute("SET TIME ZONE 'UTC'") }
        return conn
    }

    /**
     * A new connection that logs in as [user] with [password] (store-14). It reaches the server
     * through the container's port mapping, so pg_hba.conf's last line applies,
     * `host all all all scram-sha-256`, and a wrong password fails with SQLSTATE 28P01.
     */
    fun connectAs(user: String, password: String): Connection {
        val conn = DriverManager.getConnection(container.jdbcUrl, user, password)
        conn.createStatement().use { it.execute("SET TIME ZONE 'UTC'") }
        return conn
    }

    private fun load(c: PostgreSQLContainer) {
        DriverManager.getConnection(c.jdbcUrl, c.username, c.password).use { conn ->
            conn.createStatement().use { st ->
                st.execute("SET TIME ZONE 'UTC'")
                st.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
                st.execute(resource("sfz/sql/support/schema.sql"))
                st.execute(resource("sfz/sql/support/seed.sql"))
            }
        }
    }

    fun resource(path: String): String {
        val stream = Thread.currentThread().contextClassLoader.getResourceAsStream(path)
            ?: error("$path is not on the test classpath")
        return stream.bufferedReader(Charsets.UTF_8).use { it.readText() }
    }
}
