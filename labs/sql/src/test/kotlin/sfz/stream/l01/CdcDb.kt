package sfz.stream.l01

import org.testcontainers.postgresql.PostgreSQLContainer
import java.sql.Connection
import java.sql.DriverManager

/**
 * The PostgreSQL 18 server for lesson stream-01: ONE container, started on first use and shared by
 * every test of this lesson. Tests never start their own; [reset] puts the data back and drops the
 * slots a test left behind.
 *
 * It is a container of its own, not the course database (sfz.sql.support.CourseDb), because logical
 * decoding needs `wal_level = logical`, and that setting only changes with a restart. It holds one
 * table, the same `payment` table as env/kafka/cdc-init.sql:
 *
 *   pay-981  acct-17  4000  AUTHORIZED
 *   pay-982  acct-42  1250  AUTHORIZED
 *   pay-983  acct-17   999  AUTHORIZED
 */
object CdcDb {
    private class Server(val url: String, val user: String, val password: String) {
        fun connect(): Connection = DriverManager.getConnection(url, user, password)
    }

    // Started at most once per JVM. If start-up fails, the failure is remembered and rethrown,
    // so a broken start never turns into one new container per test.
    private val server: Result<Server> by lazy { runCatching { start() } }

    private fun start(): Server {
        val container = PostgreSQLContainer("postgres:18")
            .withDatabaseName("payments")
            .withUsername("sfz")
            .withPassword("sfz")
            .withCommand(
                "postgres",
                "-c", "wal_level=logical",        // replica by default: logical decoding would refuse to start
                "-c", "max_replication_slots=8",
                "-c", "fsync=off",                // the tests never crash the server itself
                "-c", "shared_buffers=32MB",
                "-c", "max_connections=20",
            )
        container.start()
        try {
            val s = Server(container.jdbcUrl, container.username, container.password)
            s.connect().use { conn ->
                conn.createStatement().use {
                    it.execute(
                        """
                        CREATE TABLE payment (
                            id          text PRIMARY KEY,
                            account     text   NOT NULL,
                            amount      bigint NOT NULL,
                            status      text   NOT NULL,
                            created_at  timestamptz NOT NULL DEFAULT now()
                        )
                        """.trimIndent(),
                    )
                }
            }
            return s
        } catch (e: Throwable) {
            container.stop()
            throw e
        }
    }

    /** A new autocommit connection to database `payments`. The caller closes it. */
    fun connect(): Connection = server.getOrThrow().connect()

    val seed = listOf(
        Payment("pay-981", "acct-17", 4000, "AUTHORIZED"),
        Payment("pay-982", "acct-42", 1250, "AUTHORIZED"),
        Payment("pay-983", "acct-17", 999, "AUTHORIZED"),
    )

    /** Drops every replication slot and reloads the three seed rows. */
    fun reset() {
        connect().use { conn ->
            conn.createStatement().use { st ->
                st.execute("SELECT pg_drop_replication_slot(slot_name) FROM pg_replication_slots")
                st.execute("TRUNCATE payment")
            }
            conn.prepareStatement("INSERT INTO payment (id, account, amount, status) VALUES (?, ?, ?, ?)").use { st ->
                for (p in seed) {
                    st.setString(1, p.id); st.setString(2, p.account); st.setLong(3, p.amount); st.setString(4, p.status)
                    st.addBatch()
                }
                st.executeBatch()
            }
        }
    }

    /** The table as the index should hold it. */
    fun rows(): Map<String, Payment> = connect().use { conn ->
        conn.createStatement().use { st ->
            st.executeQuery("SELECT id, account, amount, status FROM payment").use { rs ->
                buildMap { while (rs.next()) put(rs.getString(1), Payment(rs.getString(1), rs.getString(2), rs.getLong(3), rs.getString(4))) }
            }
        }
    }

    fun exec(conn: Connection, vararg sql: String) = conn.createStatement().use { st -> sql.forEach(st::execute) }
}
