package sfz.sql.l15

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import org.opentest4j.AssertionFailedError
import sfz.sql.support.CourseDb
import java.sql.Connection

/**
 * Lesson sql-15, exercise 2: Settings.kt in src/main/kotlin/sfz/sql/l15/, against the real
 * PostgreSQL 18 server in the test container. The container starts with a few settings on its
 * command line (see support/CourseDb.kt): shared_buffers=32MB, max_connections=20, fsync=off.
 *
 * Two tests change the server's configuration with ALTER SYSTEM and pg_reload_conf(), exactly as
 * the lesson's Try it does, and always put it back.
 */
class SettingsTest {

    @Test
    fun `each of the seven contexts maps to one way of changing a setting`() {
        assertThat(Settings.howToChange("internal")).isEqualTo(HowToChange.CANNOT)
        assertThat(Settings.howToChange("postmaster")).isEqualTo(HowToChange.RESTART)
        assertThat(Settings.howToChange("sighup")).isEqualTo(HowToChange.RELOAD)
        assertThat(Settings.howToChange("superuser-backend")).isEqualTo(HowToChange.RELOAD_FOR_NEW_SESSIONS)
        assertThat(Settings.howToChange("backend")).isEqualTo(HowToChange.RELOAD_FOR_NEW_SESSIONS)
        assertThat(Settings.howToChange("superuser")).isEqualTo(HowToChange.SET_AS_SUPERUSER)
        assertThat(Settings.howToChange("user")).isEqualTo(HowToChange.SET)
        assertThatThrownBy { Settings.howToChange("sometimes") }.isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `read returns the settings in the order asked, with their units`() = withConnection { conn ->
        // pendingRestart is left out here: once any test reloads the configuration, shared_buffers
        // reports a pending restart, because postgresql.conf says 128MB while the command line,
        // which wins, says 32MB (PostgreSQL compares the file's value with the running one)
        val got = Settings.read(conn, listOf("work_mem", "shared_buffers", "checkpoint_timeout", "wal_level"))
            .map { it.copy(pendingRestart = false) }
        assertThat(got.map { it.name }).containsExactly("work_mem", "shared_buffers", "checkpoint_timeout", "wal_level")
        assertThat(got[0]).isEqualTo(Setting("work_mem", "4096", "kB", "user", HowToChange.SET, false))
        assertThat(got[1]).describedAs("32MB in 8 kB pages").isEqualTo(Setting("shared_buffers", "4096", "8kB", "postmaster", HowToChange.RESTART, false))
        assertThat(got[2]).isEqualTo(Setting("checkpoint_timeout", "300", "s", "sighup", HowToChange.RELOAD, false))
        assertThat(got[3]).describedAs("a setting without a unit has unit null").isEqualTo(Setting("wal_level", "replica", null, "postmaster", HowToChange.RESTART, false))
    }

    @Test
    fun `the settings you change first on a new server, classified`() = withConnection { conn ->
        val expected = linkedMapOf(
            "listen_addresses" to HowToChange.RESTART,
            "max_connections" to HowToChange.RESTART,
            "shared_buffers" to HowToChange.RESTART,
            "wal_level" to HowToChange.RESTART,
            "max_wal_size" to HowToChange.RELOAD,
            "checkpoint_timeout" to HowToChange.RELOAD,
            "work_mem" to HowToChange.SET,
            "maintenance_work_mem" to HowToChange.SET,
            "effective_cache_size" to HowToChange.SET,
            "random_page_cost" to HowToChange.SET,
            "log_min_duration_statement" to HowToChange.SET_AS_SUPERUSER,
            "log_connections" to HowToChange.RELOAD_FOR_NEW_SESSIONS,
            "data_checksums" to HowToChange.CANNOT,
            "block_size" to HowToChange.CANNOT,
        )
        val got = Settings.read(conn, expected.keys.toList()).associate { it.name to it.howToChange }
        assertThat(got).isEqualTo(expected)
    }

    @Test
    fun `every setting on the server has a context the mapping knows`() = withConnection { conn ->
        val all = conn.createStatement().use { st ->
            st.executeQuery("SELECT name FROM pg_settings ORDER BY name").use { rs -> buildList { while (rs.next()) add(rs.getString(1)) } }
        }
        val got = Settings.read(conn, all)
        assertThat(got).hasSize(all.size)
        assertThat(got.count { it.howToChange == HowToChange.RESTART })
            .describedAs("PostgreSQL 18 has dozens of restart-only settings")
            .isGreaterThan(50)
    }

    @Test
    fun `an unknown setting name is an error, not a missing row`() = withConnection { conn ->
        assertThatThrownBy { Settings.read(conn, listOf("work_mem", "shared_buffer")) }
            .isInstanceOf(IllegalArgumentException::class.java)
            .hasMessageContaining("shared_buffer")
    }

    @Test
    fun `a reloadable setting takes effect after pg_reload_conf`() = withConnection { conn ->
        try {
            exec(conn, "ALTER SYSTEM SET checkpoint_timeout = '10min'")
            exec(conn, "SELECT pg_reload_conf()")
            val after = eventually("checkpoint_timeout to become 600 s after the reload") {
                Settings.read(conn, listOf("checkpoint_timeout")).single().takeIf { it.value == "600" }
            }
            assertThat(after.pendingRestart).isFalse()
            assertThat(Settings.pendingRestart(conn)).doesNotContain("checkpoint_timeout")
        } finally {
            exec(conn, "ALTER SYSTEM RESET checkpoint_timeout")
            exec(conn, "SELECT pg_reload_conf()")
        }
    }

    @Test
    fun `a restart-only setting changed with ALTER SYSTEM waits for a restart`() = withConnection { conn ->
        // max_locks_per_transaction is not on the container's command line, so the file decides it
        try {
            exec(conn, "ALTER SYSTEM SET max_locks_per_transaction = 128")
            exec(conn, "SELECT pg_reload_conf()")
            eventually("max_locks_per_transaction to show pending_restart after the reload") {
                Settings.pendingRestart(conn).takeIf { "max_locks_per_transaction" in it }
            }
            val s = Settings.read(conn, listOf("max_locks_per_transaction")).single()
            assertThat(s.value).describedAs("the running server still has the old value").isEqualTo("64")
            assertThat(s.pendingRestart).isTrue()
            assertThat(s.howToChange).isEqualTo(HowToChange.RESTART)
        } finally {
            // Taking a restart-only setting out of the file needs a restart too, so the flag stays
            // set after this RESET until the container stops. Nothing else depends on it.
            exec(conn, "ALTER SYSTEM RESET max_locks_per_transaction")
            exec(conn, "SELECT pg_reload_conf()")
        }
    }

    private fun withConnection(block: (Connection) -> Unit): Unit = CourseDb.connect().use(block)

    private fun exec(conn: Connection, sql: String) {
        conn.createStatement().use { it.execute(sql) }
    }

    /** pg_reload_conf() only sends a signal; each server process rereads the file a moment later. */
    private fun <T : Any> eventually(what: String, probe: () -> T?): T {
        val deadline = System.nanoTime() + 5_000_000_000L
        while (System.nanoTime() < deadline) {
            probe()?.let { return it }
            Thread.sleep(50)
        }
        throw AssertionFailedError("waited 5 s for $what")
    }
}
