package sfz.store.l07

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import sfz.sql.support.CourseDb
import sfz.sql.support.Plan
import sfz.sql.support.Tx
import sfz.sql.support.exerciseSql
import sfz.sql.support.explain
import sfz.sql.support.rollback
import sfz.sql.support.row
import java.time.Instant

/**
 * Lesson store-07. Your statements are in src/main/resources/sfz/store/l07/.
 *
 * An index only shows its worth on a table bigger than a few pages, so most of these tests run
 * your statement on a 200,000-row copy of payments in schema lab11 (built once, below, and
 * vacuumed so that index-only scans can skip the table). Each test is still a transaction that
 * is rolled back, so the index you create is gone before the next test.
 */
class IndexesTest {

    companion object {
        @JvmStatic
        @BeforeAll
        fun buildCopy() {
            CourseDb.connect().use { conn ->
                conn.createStatement().use { st ->
                    // the test server runs with synchronous_commit=off; VACUUM may only mark a page
                    // all-visible once the commit that filled it is flushed, so flush this one
                    st.execute("SET synchronous_commit = on")
                    st.execute("DROP SCHEMA IF EXISTS lab11 CASCADE")
                    st.execute("CREATE SCHEMA lab11")
                    // same columns, defaults, checks, primary key and unique index; no foreign keys
                    st.execute("CREATE TABLE lab11.payments (LIKE public.payments INCLUDING ALL)")
                    // 200,000 payments every 75 seconds from 1 January (to about 22 June).
                    // Merchants 1 to 5 share almost all of them; 6 and 8 get one in a thousand each.
                    st.execute(
                        """
                        INSERT INTO lab11.payments (payment_id, card_id, merchant_id, amount_minor, status, created_at)
                        SELECT g,
                               1 + g % 14,
                               CASE WHEN g % 1000 = 7 THEN 6 WHEN g % 1000 = 507 THEN 8 ELSE 1 + g % 5 END,
                               100 + (g * 7919) % 90000,
                               CASE WHEN g % 50 = 0 THEN 'failed' WHEN g % 97 = 0 THEN 'pending' ELSE 'succeeded' END,
                               timestamptz '2026-01-01 00:00+00' + g * interval '75 seconds'
                        FROM generate_series(1, 200000) AS g
                        """,
                    )
                    // statistics for the planner, and a visibility map for index-only scans
                    st.execute("VACUUM (ANALYZE) lab11.payments")
                }
            }
        }

        private const val DASHBOARD = """
            SELECT payment_id, amount_minor, created_at
            FROM payments
            WHERE merchant_id = %d
              AND created_at >= '%s' AND created_at < '%s'
            ORDER BY created_at DESC
            LIMIT 20"""

        private const val STATEMENT = """
            SELECT count(*) AS payments, sum(amount_minor) AS gross_minor
            FROM payments
            WHERE merchant_id = 6 AND status = 'succeeded'
              AND created_at >= '2026-03-01' AND created_at < '2026-04-01'"""
    }

    /** Point this transaction at the 200,000-row copy; public still supplies the other tables. */
    private fun Tx.onTheCopy() = script("SET LOCAL search_path = lab11, public")

    private fun Plan.assertIndexScanOnPayments() {
        val scan = scanOf("payments") ?: fail("no node reads payments")
        if (!(scan.name.startsWith("Index Scan") || scan.name.startsWith("Index Only Scan"))) {
            fail("expected an Index Scan or Index Only Scan on payments, found: ${scan.name}")
        }
    }

    // ---------------------------------------------------------------- merchant_month_index

    @Test
    fun `merchant_month_index lets the dashboard read merchant 6's March in a few pages`() = rollback {
        onTheCopy()
        runExercise("store/l07", "merchant_month_index")
        val plan = explain(DASHBOARD.format(6, "2026-03-01", "2026-04-01"))
        plan.assertIndexScanOnPayments()
        if (plan.has("Sort")) plan.fail("the rows should come out of the index already in created_at order, without a Sort")
        if (plan.buffers > 40) plan.fail("expected at most 40 buffers, the query read ${plan.buffers}")
    }

    @Test
    fun `merchant_month_index serves another merchant and month, and returns the newest twenty`() = rollback {
        onTheCopy()
        // merchant 7 had no payments in the copy: 30 arrive in May, one every 13 hours
        update(
            """
            INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at)
            SELECT 300000 + k, 13, 7, 1000 + k, 'succeeded', timestamptz '2026-05-01 06:00+00' + k * interval '13 hours'
            FROM generate_series(1, 30) AS k
            """,
        )
        runExercise("store/l07", "merchant_month_index")
        val sql = DASHBOARD.format(7, "2026-05-01", "2026-06-01")
        val plan = explain(sql)
        plan.assertIndexScanOnPayments()
        if (plan.has("Sort")) plan.fail("the rows should come out of the index already in created_at order, without a Sort")
        if (plan.buffers > 40) plan.fail("expected at most 40 buffers, the query read ${plan.buffers}")
        val ids = query(sql).column("payment_id")
        assertThat(ids).describedAs("the 20 newest of merchant 7's May payments, newest first")
            .isEqualTo((30 downTo 11).map { 300000L + it })
    }

    // ---------------------------------------------------------------- payments_on_day

    private fun t(s: String): Instant = Instant.parse(s)

    @Test
    fun `payments_on_day returns the payments of 12 March`() = rollback {
        val rows = exercise("store/l07", "payments_on_day")
        rows.assertColumns("payment_id", "created_at")
        rows.assertRowsInOrder(
            row(17, t("2026-03-12T16:40:00Z")),
            row(18, t("2026-03-12T16:42:10Z")),
        )
    }

    @Test
    fun `payments_on_day keeps midnight and the last half second, and drops the 13th`() = rollback {
        update(
            """
            INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES
              (100, 1, 1, 100, 'succeeded', '2026-03-12 00:00:00+00'),
              (101, 1, 1, 100, 'succeeded', '2026-03-12 23:59:59.5+00'),
              (102, 1, 1, 100, 'succeeded', '2026-03-13 00:00:00+00'),
              (103, 1, 1, 100, 'succeeded', '2026-03-11 23:59:59.999999+00')
            """,
        )
        exercise("store/l07", "payments_on_day").assertRowsInOrder(
            row(100, t("2026-03-12T00:00:00Z")),
            row(17, t("2026-03-12T16:40:00Z")),
            row(18, t("2026-03-12T16:42:10Z")),
            row(101, t("2026-03-12T23:59:59.500Z")),
        )
    }

    @Test
    fun `payments_on_day searches an index on created_at instead of filtering every row`() = rollback {
        onTheCopy()
        script("CREATE INDEX lab_created_at_idx ON payments (created_at)")
        val plan = explain(exerciseSql("store/l07", "payments_on_day"))
        val cond = plan.nodes.mapNotNull { it.detail("Index Cond") }.firstOrNull { "created_at" in it }
            ?: plan.fail("expected an Index Cond on created_at: the index should find the day's first entry and read to its last")
        val filtered = plan.nodes.mapNotNull { it.detail("Filter") }.firstOrNull { "created_at" in it }
        if (filtered != null) plan.fail("created_at is still tested in a Filter, row by row: $filtered")
        assertThat(cond).isNotBlank()
        if (plan.buffers > 100) plan.fail("expected at most 100 buffers for one day, the query read ${plan.buffers}")
    }

    // ---------------------------------------------------------------- merchant_gross_index

    @Test
    fun `merchant_gross_index answers the statement without reading the table`() = rollback {
        onTheCopy()
        runExercise("store/l07", "merchant_gross_index")
        val plan = explain(STATEMENT)
        val scan = plan.scanOf("payments") ?: plan.fail("no node reads payments")
        if (!scan.name.startsWith("Index Only Scan")) plan.fail("expected an Index Only Scan on payments, found: ${scan.name}")
        assertThat(scan.detail("Heap Fetches")).describedAs("Heap Fetches").isEqualTo("0")
    }

    @Test
    fun `merchant_gross_index still covers the statement after new payments arrive`() = rollback {
        onTheCopy()
        update(
            """
            INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at)
            SELECT 300000 + k, 2, 6, 5000, CASE WHEN k = 5 THEN 'failed' ELSE 'succeeded' END,
                   timestamptz '2026-03-20 12:00+00' + k * interval '1 minute'
            FROM generate_series(1, 5) AS k
            """,
        )
        val expected = query(STATEMENT).rows.single()      // before any new index: computed from the table
        runExercise("store/l07", "merchant_gross_index")
        val plan = explain(STATEMENT)
        val scan = plan.scanOf("payments") ?: plan.fail("no node reads payments")
        if (!scan.name.startsWith("Index Only Scan")) plan.fail("expected an Index Only Scan on payments, found: ${scan.name}")
        // the new rows sit on a page that VACUUM has not seen yet: only they need a visit to the table
        val fetches = scan.detail("Heap Fetches")?.toInt() ?: plan.fail("no Heap Fetches line")
        assertThat(fetches).describedAs("Heap Fetches: at most the 5 new rows").isLessThanOrEqualTo(5)
        assertThat(query(STATEMENT).rows.single()).isEqualTo(expected)
    }
}
