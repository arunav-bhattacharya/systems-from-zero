package sfz.sql.l15

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.opentest4j.AssertionFailedError
import sfz.sql.support.CourseDb
import sfz.sql.support.Tx
import sfz.sql.support.exerciseSql
import sfz.sql.support.row
import java.sql.SQLException

/**
 * Lesson sql-15, exercise 3: src/main/resources/sfz/sql/l15/least_privilege.sql.
 *
 * Before the tests, the superuser builds schema ledger (test resource sfz/sql/l15/ledger_schema.sql)
 * and runs your file, both committed: a role has to exist for real before anyone can log in as it.
 * Each test then logs in as payments_app with its password, over TCP, and runs its statements
 * in a transaction that is rolled back. Afterwards everything is dropped again.
 */
class LeastPrivilegeTest {

    companion object {
        private const val APP = "payments_app"
        private const val PASSWORD = "app-pass"

        @JvmStatic
        @BeforeAll
        fun createSchemaAndRole() {
            dropEverything()
            asSuperuser(CourseDb.resource("sfz/sql/l15/ledger_schema.sql"), "ledger_schema.sql")
            asSuperuser(exerciseSql(15, "least_privilege"), "sfz/sql/l15/least_privilege.sql")
        }

        @JvmStatic
        @AfterAll
        fun dropEverything() {
            CourseDb.connect().use { conn ->
                conn.createStatement().use { st ->
                    st.execute("DROP SCHEMA IF EXISTS ledger CASCADE")
                    for (role in listOf(APP, "ledger_owner")) {
                        val exists = st.executeQuery("SELECT 1 FROM pg_roles WHERE rolname = '$role'").use { it.next() }
                        if (exists) {
                            st.execute("DROP OWNED BY $role")    // revokes its grants and default privileges too
                            st.execute("DROP ROLE $role")
                        }
                    }
                }
            }
        }

        private fun asSuperuser(sql: String, label: String) {
            CourseDb.connect().use { conn ->
                try {
                    conn.createStatement().use { it.execute(sql) }
                } catch (e: SQLException) {
                    throw AssertionFailedError("$label failed with SQLSTATE ${e.sqlState}: ${e.message}", e)
                }
            }
        }
    }

    /** Logs in as payments_app and runs [block] in a transaction that is always rolled back. */
    private fun asApp(block: Tx.() -> Unit) {
        val conn = try {
            CourseDb.connectAs(APP, PASSWORD)
        } catch (e: SQLException) {
            throw AssertionFailedError("could not log in as $APP with password '$PASSWORD': SQLSTATE ${e.sqlState}: ${e.message}", e)
        }
        conn.use {
            it.autoCommit = false
            try {
                Tx(it).block()
            } finally {
                it.rollback()
            }
        }
    }

    private fun Tx.allowed(sql: String) {
        val state = sqlStateOf(sql)
        if (state != null) throw AssertionFailedError("$APP should be allowed to run this, but it failed with SQLSTATE $state:\n  $sql")
    }

    private fun Tx.refused(sql: String) {
        val state = sqlStateOf(sql)
        if (state != "42501") {
            throw AssertionFailedError(
                (if (state == null) "$APP ran this, and it should not be allowed to:" else "expected SQLSTATE 42501, got $state:") + "\n  $sql",
                "42501", state ?: "success",
            )
        }
    }

    @Test
    fun `payments_app logs in with its password and is an ordinary role`() = asApp {
        query("SELECT current_user, rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user")
            .assertRowsInOrder(row(APP, false, false, false))
    }

    @Test
    fun `a wrong password is refused with 28P01`() {
        val state = try {
            CourseDb.connectAs(APP, "app-pass2").close()
            null
        } catch (e: SQLException) {
            e.sqlState
        }
        assertThat(state).describedAs("password authentication failed").isEqualTo("28P01")
    }

    @Test
    fun `it reads and writes payments and refunds`() = asApp {
        query("SELECT count(*) FROM ledger.payments").assertRowsInOrder(row(3))
        allowed("INSERT INTO ledger.payments (merchant_id, amount_minor, status) VALUES (3, 4200, 'pending')")
        allowed("UPDATE ledger.payments SET status = 'succeeded' WHERE status = 'pending'")
        allowed("INSERT INTO ledger.refunds (payment_id, amount_minor) VALUES (2, 200)")
        allowed("UPDATE ledger.refunds SET amount_minor = 250 WHERE payment_id = 2")
        query("SELECT count(*) FROM ledger.refunds").assertRowsInOrder(row(2))
    }

    @Test
    fun `it never deletes or truncates payments or refunds`() = asApp {
        refused("DELETE FROM ledger.payments WHERE payment_id = 3")
        refused("DELETE FROM ledger.refunds")
        refused("TRUNCATE ledger.payments CASCADE")
        refused("TRUNCATE ledger.refunds")
    }

    @Test
    fun `it appends to the audit log and can never read or change it`() = asApp {
        allowed("INSERT INTO ledger.audit_log (action) VALUES ('payment 4 captured')")
        refused("SELECT * FROM ledger.audit_log")
        refused("SELECT count(*) FROM ledger.audit_log")
        refused("UPDATE ledger.audit_log SET action = 'nothing happened'")
        refused("DELETE FROM ledger.audit_log")
        refused("TRUNCATE ledger.audit_log")
    }

    @Test
    fun `it cannot drop or alter tables, even with every table privilege`() = asApp {
        refused("DROP TABLE ledger.refunds")
        refused("ALTER TABLE ledger.payments ADD COLUMN note text")
        refused("CREATE INDEX ON ledger.payments (merchant_id)")
    }

    @Test
    fun `it creates nothing, in ledger or in public, and no roles`() = asApp {
        refused("CREATE TABLE ledger.scratch (id int)")
        refused("CREATE TABLE public.scratch (id int)")
        refused("CREATE ROLE sneaky LOGIN")
    }

    @Test
    fun `it cannot read the course tables in public`() = asApp {
        refused("SELECT count(*) FROM public.payments")
        refused("SELECT email FROM public.customers")
    }

    @Test
    fun `a table ledger_owner creates later works without a new GRANT`() {
        asSuperuser(
            """
            SET ROLE ledger_owner;
            CREATE TABLE ledger.chargebacks (
                chargeback_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                payment_id    bigint NOT NULL REFERENCES ledger.payments,
                reason        text NOT NULL
            );
            RESET ROLE;
            """.trimIndent(),
            "creating ledger.chargebacks as ledger_owner",
        )
        asApp {
            allowed("INSERT INTO ledger.chargebacks (payment_id, reason) VALUES (1, 'fraud')")
            allowed("UPDATE ledger.chargebacks SET reason = 'not received'")
            query("SELECT count(*) FROM ledger.chargebacks").assertRowsInOrder(row(1))
            refused("DELETE FROM ledger.chargebacks")
        }
    }
}
