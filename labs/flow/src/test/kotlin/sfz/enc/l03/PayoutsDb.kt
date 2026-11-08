package sfz.enc.l03

import org.testcontainers.postgresql.PostgreSQLContainer
import java.sql.Connection
import java.sql.DriverManager

/**
 * One PostgreSQL 18 container for the whole test JVM, started on first use.
 * [reset] recreates the `payouts` table in its starting shape with 1,000 rows written by version 1.
 */
object PayoutsDb {
    private val container: PostgreSQLContainer by lazy {
        PostgreSQLContainer("postgres:18")
            .withDatabaseName("sfz")
            .withUsername("sfz")
            .withPassword("sfz")
            // small and fast: the data is tiny, and losing it on a crash costs nothing
            .withCommand("postgres", "-c", "fsync=off", "-c", "synchronous_commit=off", "-c", "shared_buffers=32MB", "-c", "max_connections=20")
            .also { it.start() }
    }

    fun connect(): Connection = container.let { DriverManager.getConnection(it.jdbcUrl, it.username, it.password) }

    /** Drops and recreates `payouts` with ids 1 to 1,000; payout n is worth n * 7 cents. */
    fun reset(conn: Connection) {
        conn.createStatement().use { st ->
            st.execute("DROP TABLE IF EXISTS payouts")
            st.execute("CREATE TABLE payouts (id bigint PRIMARY KEY, merchant text NOT NULL, amount numeric(12,2) NOT NULL)")
            st.execute("INSERT INTO payouts SELECT g, 'merchant-' || (g % 50), g * 7 / 100.0 FROM generate_series(1, 1000) g")
        }
    }

    fun columns(conn: Connection): Map<String, Boolean> =
        conn.prepareStatement(
            "SELECT column_name, is_nullable = 'YES' FROM information_schema.columns WHERE table_name = 'payouts' ORDER BY ordinal_position"
        ).use { st -> st.executeQuery().use { rs -> buildMap { while (rs.next()) put(rs.getString(1), rs.getBoolean(2)) } } }

    fun count(conn: Connection, sql: String): Long =
        conn.createStatement().use { st -> st.executeQuery(sql).use { rs -> rs.next(); rs.getLong(1) } }
}
