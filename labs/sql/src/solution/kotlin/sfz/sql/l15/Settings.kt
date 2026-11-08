package sfz.sql.l15

import java.sql.Connection

/** What it takes for a new value of a setting to take effect, read from `pg_settings.context`. */
enum class HowToChange {
    /** internal: fixed when PostgreSQL was built or initdb ran (block_size, data_checksums). */
    CANNOT,

    /** postmaster: change the file (or ALTER SYSTEM), then restart the server. */
    RESTART,

    /** sighup: change the file, then reload (`SELECT pg_reload_conf()`); every process picks it up. */
    RELOAD,

    /** backend and superuser-backend: reload; only sessions that start after it see the new value. */
    RELOAD_FOR_NEW_SESSIONS,

    /** superuser: reload, or `SET` it in one session, as a superuser or a role granted SET on it. */
    SET_AS_SUPERUSER,

    /** user: reload, or `SET` it in one session; any role may. */
    SET,
}

/** One row of pg_settings. [value] is pg_settings.setting, in [unit] (shared_buffers "16384" in "8kB"). */
data class Setting(
    val name: String,
    val value: String,
    val unit: String?,
    val context: String,
    val howToChange: HowToChange,
    val pendingRestart: Boolean,
)

/**
 * Lesson sql-15, exercise 2 of 3: read settings from a running server and say how each one changes.
 * The tests run these against PostgreSQL 18 in a container.
 */
object Settings {

    /**
     * Maps a `pg_settings.context` value to [HowToChange]. The seven contexts are internal,
     * postmaster, sighup, superuser-backend, backend, superuser and user (see the KDoc on each
     * constant). Throw IllegalArgumentException for anything else.
     */
    fun howToChange(context: String): HowToChange = when (context) {
        "internal" -> HowToChange.CANNOT
        "postmaster" -> HowToChange.RESTART
        "sighup" -> HowToChange.RELOAD
        "superuser-backend", "backend" -> HowToChange.RELOAD_FOR_NEW_SESSIONS
        "superuser" -> HowToChange.SET_AS_SUPERUSER
        "user" -> HowToChange.SET
        else -> throw IllegalArgumentException("unknown pg_settings context '$context'")
    }

    /**
     * Reads [names] from pg_settings on [conn] and returns one [Setting] per name, in the order
     * of [names]. Use the columns name, setting, unit, context and pending_restart, and
     * [howToChange] for the classification. A name the server does not know is a mistake in the
     * caller: throw IllegalArgumentException naming it.
     */
    fun read(conn: Connection, names: List<String>): List<Setting> {
        val found = conn.prepareStatement(
            "SELECT name, setting, unit, context, pending_restart FROM pg_settings WHERE name = ANY (?)",
        ).use { ps ->
            ps.setArray(1, conn.createArrayOf("text", names.toTypedArray()))   // one round trip for all names
            ps.executeQuery().use { rs ->
                buildMap {
                    while (rs.next()) {
                        val context = rs.getString("context")
                        put(
                            rs.getString("name"),
                            Setting(
                                name = rs.getString("name"),
                                value = rs.getString("setting"),
                                unit = rs.getString("unit"),               // NULL for settings without a unit
                                context = context,
                                howToChange = howToChange(context),
                                pendingRestart = rs.getBoolean("pending_restart"),
                            ),
                        )
                    }
                }
            }
        }
        return names.map { found[it] ?: throw IllegalArgumentException("no setting named '$it'") }
    }

    /**
     * The names of the settings whose new value waits for a restart (pending_restart is true),
     * sorted by name. After `ALTER SYSTEM SET shared_buffers = '256MB'` and a reload, this
     * returns [shared_buffers].
     */
    fun pendingRestart(conn: Connection): List<String> =
        conn.createStatement().use { st ->
            st.executeQuery("SELECT name FROM pg_settings WHERE pending_restart ORDER BY name").use { rs ->
                buildList { while (rs.next()) add(rs.getString(1)) }
            }
        }
}
