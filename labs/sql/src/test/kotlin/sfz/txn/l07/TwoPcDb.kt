package sfz.txn.l07

import org.testcontainers.postgresql.PostgreSQLContainer
import java.sql.Connection
import java.sql.DriverManager

/**
 * The PostgreSQL 18 server for lesson txn-07: ONE container for the whole test JVM, started on
 * first use and shared by every test. Tests never start their own; [reset] puts the data back.
 *
 * It is a container of its own, not the course database (sfz.sql.support.CourseDb), because
 * prepared transactions are switched off by default (`max_prepared_transactions = 0`) and the
 * setting can only change with a restart. It holds two databases that stand for two machines:
 *
 *   wallets   wallets(id, balance_minor)                       w-17: 10000, w-18: 5000
 *   payouts   merchant_balances(id, balance_minor)              m-cafe: 0
 *             payout_entries(transfer_id PRIMARY KEY, ...)      txf-dup is already there
 *
 * PostgreSQL can't run one transaction across two databases, even on one server, so to a
 * coordinator they are as separate as two servers.
 */
object TwoPcDb {
    private class Server(val container: PostgreSQLContainer) {
        val baseUrl: String = container.jdbcUrl
        val user: String = container.username
        val password: String = container.password

        fun url(db: String): String = baseUrl.replace(Regex("/sfz(\\?|$)"), "/$db$1")
        fun connect(db: String): Connection = DriverManager.getConnection(url(db), user, password)
    }

    // Started at most once per JVM. If start-up fails, the failure is remembered and rethrown,
    // so a broken start never turns into one new container per test.
    private val server: Result<Server> by lazy { runCatching { start() } }

    private fun start(): Server {
        val container = PostgreSQLContainer("postgres:18")
            .withDatabaseName("sfz")
            .withUsername("sfz")
            .withPassword("sfz")
            .withCommand(
                "postgres",
                "-c", "max_prepared_transactions=10", // 0 by default: PREPARE TRANSACTION would fail
                "-c", "fsync=off",                     // the tests never crash the server itself
                "-c", "shared_buffers=32MB",
                "-c", "max_connections=30",
            )
        container.start()
        try {
            val s = Server(container)
            create(s) // uses the Server it was given, never this object's lazy property
            return s
        } catch (e: Throwable) {
            container.stop()
            throw e
        }
    }

    private fun create(s: Server) {
        s.connect("sfz").use { conn ->
            conn.createStatement().use { st ->
                st.execute("CREATE DATABASE wallets")
                st.execute("CREATE DATABASE payouts")
            }
        }
        s.connect("wallets").use { conn ->
            conn.createStatement().use {
                it.execute("CREATE TABLE wallets (id text PRIMARY KEY, balance_minor bigint NOT NULL CHECK (balance_minor >= 0))")
            }
        }
        s.connect("payouts").use { conn ->
            conn.createStatement().use {
                it.execute("CREATE TABLE merchant_balances (id text PRIMARY KEY, balance_minor bigint NOT NULL)")
                it.execute(
                    "CREATE TABLE payout_entries (transfer_id text PRIMARY KEY, merchant_id text NOT NULL, amount_minor bigint NOT NULL)",
                )
            }
        }
    }

    private const val WALLETS_SEED = """
        TRUNCATE wallets;
        INSERT INTO wallets (id, balance_minor) VALUES ('w-17', 10000), ('w-18', 5000);
    """
    private const val PAYOUTS_SEED = """
        TRUNCATE merchant_balances, payout_entries;
        INSERT INTO merchant_balances (id, balance_minor) VALUES ('m-cafe', 0);
        INSERT INTO payout_entries (transfer_id, merchant_id, amount_minor) VALUES ('txf-dup', 'm-cafe', 3000);
    """

    /** A new autocommit connection to database [db] ("wallets", "payouts" or "sfz"). The caller closes it. */
    fun connect(db: String): Connection = server.getOrThrow().connect(db)

    /** Every prepared transaction on the server, any database, as gids sorted. */
    fun preparedGids(): List<String> = connect("sfz").use { conn ->
        conn.createStatement().use { st ->
            st.executeQuery("SELECT gid FROM pg_prepared_xacts ORDER BY gid").use { rs ->
                buildList { while (rs.next()) add(rs.getString(1)) }
            }
        }
    }

    /**
     * Puts the server back between tests: cancels any session still waiting for a lock, rolls back
     * every prepared transaction a test left behind, and reloads the seed in both databases.
     */
    fun reset() {
        connect("sfz").use { conn ->
            conn.createStatement().use {
                it.execute("SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE wait_event_type = 'Lock'")
            }
            val left = conn.createStatement().use { st ->
                st.executeQuery("SELECT gid, database FROM pg_prepared_xacts").use { rs ->
                    buildList { while (rs.next()) add(rs.getString(1) to rs.getString(2)) }
                }
            }
            for ((gid, db) in left) {
                connect(db).use { d -> d.createStatement().use { it.execute("ROLLBACK PREPARED '$gid'") } }
            }
        }
        connect("wallets").use { c -> c.createStatement().use { it.execute(WALLETS_SEED) } }
        connect("payouts").use { c -> c.createStatement().use { it.execute(PAYOUTS_SEED) } }
    }

    /** One number from one query, such as a balance. */
    fun long(db: String, sql: String): Long = connect(db).use { conn ->
        conn.createStatement().use { st -> st.executeQuery(sql).use { rs -> check(rs.next()) { "no row: $sql" }; rs.getLong(1) } }
    }
}
