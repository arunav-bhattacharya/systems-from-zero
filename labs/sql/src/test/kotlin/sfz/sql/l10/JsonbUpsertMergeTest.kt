package sfz.sql.l10

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.sql.support.Tx
import sfz.sql.support.exerciseSql
import sfz.sql.support.rollback
import sfz.sql.support.row
import sfz.sql.support.sessions

/**
 * Lesson sql-10. Your statements are in src/main/resources/sfz/sql/l10/. Each test runs in a
 * transaction that is rolled back, except the one that runs two sessions at once: that one
 * commits, and deletes what it added afterwards.
 */
class JsonbUpsertMergeTest {

    // ---------------------------------------------------------------- risky_payments

    private val risky = listOf(
        row(3, "web", 91), row(15, "web", 88), row(18, "android", 79), row(31, "web", 72),
        row(8, "web", 67), row(36, "ios", 61), row(27, "android", 57), row(23, "web", 52),
    )

    @Test
    fun `risky_payments compares scores as numbers`() = rollback {
        val rows = exercise(10, "risky_payments")
        rows.assertColumns("payment_id", "channel", "score")
        // as text, '8' >= '50' (because '8' > '5'): payments 2, 12, 14, 21, 25 and 34 must not appear
        rows.assertRowsInOrder(*risky.toTypedArray())
    }

    @Test
    fun `risky_payments follows new documents`() = rollback {
        update(
            """
            INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at, metadata) VALUES
              (100, 1, 1, 500, 'succeeded', '2026-06-20 10:00+00', '{"channel": "pos", "risk": {"score": 9, "rules": ["velocity"]}}'),
              (101, 1, 1, 500, 'succeeded', '2026-06-20 10:01+00', '{"channel": "web", "risk": {"score": 12, "rules": ["velocity_hourly"]}}'),
              (102, 2, 2, 700, 'succeeded', '2026-06-20 10:02+00', '{"channel": "ios"}'),
              (103, 2, 2, 900, 'failed',    '2026-06-20 10:03+00', '{"channel": "android", "risk": {"score": 100, "rules": []}}'),
              (104, 4, 3, 275, 'succeeded', '2026-06-20 10:04+00', '{"channel": "web", "risk": {"rules": ["geo_mismatch", "velocity"]}}')
            """,
        )
        exercise(10, "risky_payments").assertRowsInOrder(
            row(103, "android", 100),          // as text, '100' < '50'
            *risky.toTypedArray(),
            row(100, "pos", 9),                // low score, but the velocity rule fired
            row(104, "web", null),             // velocity and no score at all: last
        )                                      // 101 ("velocity_hourly") and 102 (no risk) stay out
    }

    // ---------------------------------------------------------------- ingest_payment

    private val uid20 = "019d0ab9-28c0-7014-8000-000000000014"   // payment 20: pending
    private val uid17 = "019ce2eb-5700-7011-8000-000000000011"   // payment 17: succeeded
    private val uidNew = "019f1d1f-0500-7000-8000-0000000a0001"  // no payment has it

    private data class Message(val uid: String, val card: Int, val merchant: Int, val amount: Int, val status: String, val at: String)

    private val capture20 = Message(uid20, 3, 1, 7425, "succeeded", "2026-03-20 10:10+00")
    private val newPayment = Message(uidNew, 1, 1, 4200, "pending", "2026-07-01 10:00+00")

    private fun valuesOf(messages: List<Message>) = messages.joinToString(",\n") { m ->
        "('${m.uid}'::uuid, ${m.card}::bigint, ${m.merchant}::bigint, ${m.amount}::bigint, '${m.status}'::text, '${m.at}'::timestamptz)"
    }

    private val inboundColumns = "(payment_uid, card_id, merchant_id, amount_minor, status, created_at)"

    /** The temporary table the exercise reads its messages from, in this transaction. */
    private fun Tx.inbound(vararg messages: Message) {
        script("DROP TABLE IF EXISTS pg_temp.inbound")
        script("CREATE TEMP TABLE inbound AS SELECT * FROM (VALUES ${valuesOf(messages.toList())}) AS m $inboundColumns")
    }

    private fun Tx.status(paymentId: Int): Any? = query("SELECT status FROM payments WHERE payment_id = ?", paymentId.toLong()).rows.single()[0]

    private fun Tx.paymentCount(): Any? = query("SELECT count(*) FROM payments").rows.single()[0]

    @Test
    fun `ingest_payment applies a capture to a pending payment`() = rollback {
        inbound(capture20)
        val rows = exercise(10, "ingest_payment")
        rows.assertColumns("payment_id", "old_status", "new_status")
        rows.assertRowsInOrder(row(20, "pending", "succeeded"))
        assertThat(status(20)).isEqualTo("succeeded")
        assertThat(paymentCount()).describedAs("no new payment row").isEqualTo(37L)
    }

    @Test
    fun `ingest_payment inserts a new payment once, however often it arrives`() = rollback {
        inbound(newPayment)
        val first = exercise(10, "ingest_payment")
        val id = query("SELECT payment_id FROM payments WHERE payment_uid = ?::uuid", uidNew).rows.single()[0]
        first.assertRowsInOrder(row(id, null, "pending"))
        exercise(10, "ingest_payment").assertRowsInOrder()          // the second delivery changes nothing
        assertThat(paymentCount()).isEqualTo(38L)
    }

    @Test
    fun `ingest_payment handles a batch of new, repeated, late and final messages`() = rollback {
        update(
            "INSERT INTO payments (payment_id, payment_uid, card_id, merchant_id, amount_minor, status, created_at) " +
                "VALUES (9100, '019f2c00-0000-7000-8000-000000000100', 9, 3, 275, 'pending', '2026-07-02 08:00+00')",
        )
        inbound(
            Message("019f2c00-0000-7000-8000-000000000100", 9, 3, 275, "failed", "2026-07-02 08:00+00"),   // final status for 9100
            Message(uid17, 8, 4, 18999, "succeeded", "2026-03-12 16:40+00"),                              // repeat of a done payment
            Message("019ce2ed-52d0-7012-8000-000000000012", 8, 4, 18999, "pending", "2026-03-12 16:42:10+00"), // late pending for 18
            Message(uid20, 3, 1, 7425, "pending", "2026-03-20 10:10+00"),                                 // pending again: no change
            Message("019f2c00-0000-7000-8000-000000000200", 12, 7, 1980, "failed", "2026-07-02 09:00+00"), // new, and already final
        )
        val rows = exercise(10, "ingest_payment")
        val newId = query("SELECT payment_id FROM payments WHERE payment_uid = '019f2c00-0000-7000-8000-000000000200'").rows.single()[0]
        rows.assertRowsAnyOrder(row(9100, "pending", "failed"), row(newId, null, "failed"))
        assertThat(status(17)).isEqualTo("succeeded")
        assertThat(status(18)).describedAs("a late 'pending' never undoes a final status").isEqualTo("succeeded")
        assertThat(status(20)).isEqualTo("pending")
        assertThat(paymentCount()).isEqualTo(39L)
    }

    @Test
    fun `ingest_payment stores a message once when two sessions ingest it at the same moment`() =
        sessions(cleanup = "DELETE FROM payments WHERE payment_uid = '$uidNew'") {
            val create = "CREATE TEMP TABLE inbound AS SELECT * FROM (VALUES ${valuesOf(listOf(newPayment))}) AS m $inboundColumns"
            a.run(create)
            b.run(create)
            val ingest = exerciseSql(10, "ingest_payment")

            a.run("BEGIN")
            assertThat(a.run(ingest)?.size).describedAs("session A inserts the payment").isEqualTo(1)
            val second = b.start(ingest)          // B ingests the same message before A commits
            second.awaitBlocked()                 // the unique index makes B wait for A's transaction
            a.run("COMMIT")
            assertThat(second.sqlState())
                .describedAs("session B must not fail: once A commits, B's message is a repeat (23505 means the race got through)")
                .isNull()
            assertThat(second.result()?.size ?: 0).describedAs("B changed nothing, so it returns no rows").isEqualTo(0)
            val stored = a.run("SELECT count(*) FROM payments WHERE payment_uid = '$uidNew'")!!.rows.single()[0]
            assertThat(stored).isEqualTo(1L)
        }

    // ---------------------------------------------------------------- settle_month

    /** The totals table with last night's numbers: March is stale, February is final. */
    private fun Tx.lastNightsTotals() {
        script(
            """
            CREATE TABLE merchant_month_totals (
                merchant_id    bigint NOT NULL REFERENCES merchants,
                month          date   NOT NULL,
                gross_minor    bigint NOT NULL,
                payment_count  int    NOT NULL,
                PRIMARY KEY (merchant_id, month)
            );
            INSERT INTO merchant_month_totals VALUES
                (1, '2026-02-01',   8620, 2),
                (4, '2026-02-01',  54999, 1),
                (1, '2026-03-01',   5310, 1),    -- right
                (2, '2026-03-01',   2150, 1),    -- Blue Fern has no succeeded March payment: delete
                (4, '2026-03-01',  37998, 2),    -- payment 19 came in late: update
                (5, '2026-03-01', 147500, 3);    -- right
            """,                                 // Quick Bite (7) has no row: insert
        )
    }

    private fun Tx.totals() = query("SELECT merchant_id, month::text, gross_minor, payment_count FROM merchant_month_totals ORDER BY month, merchant_id")

    @Test
    fun `settle_month inserts, updates and deletes only what March needs`() = rollback {
        lastNightsTotals()
        val rows = exercise(10, "settle_month")
        rows.assertColumns("action", "merchant_id", "old_gross", "new_gross")
        rows.assertRowsAnyOrder(
            row("DELETE", 2, 2150, null),
            row("UPDATE", 4, 37998, 56997),
            row("INSERT", 7, null, 1325),
        )
        totals().assertRowsInOrder(
            row(1, "2026-02-01", 8620, 2), row(4, "2026-02-01", 54999, 1),      // other months untouched
            row(1, "2026-03-01", 5310, 1), row(4, "2026-03-01", 56997, 3),
            row(5, "2026-03-01", 147500, 3), row(7, "2026-03-01", 1325, 1),
        )
    }

    @Test
    fun `settle_month follows new payments and leaves other months alone`() = rollback {
        lastNightsTotals()
        update(
            """
            INSERT INTO payments (payment_id, card_id, merchant_id, amount_minor, status, created_at) VALUES
              (100, 2, 2, 3000, 'succeeded', '2026-03-15 12:00+00'),   -- Blue Fern's first succeeded March payment
              (101, 2, 8, 500,  'pending',   '2026-03-16 12:00+00'),   -- pending: not in the totals
              (102, 7, 5, 100,  'failed',    '2026-03-17 12:00+00'),   -- failed: not in the totals
              (103, 1, 1, 990,  'succeeded', '2026-02-10 12:00+00')    -- February: this MERGE is only about March
            """,
        )
        exercise(10, "settle_month").assertRowsAnyOrder(
            row("UPDATE", 2, 2150, 3000),
            row("UPDATE", 4, 37998, 56997),
            row("INSERT", 7, null, 1325),
        )
        totals().assertRowsInOrder(
            row(1, "2026-02-01", 8620, 2), row(4, "2026-02-01", 54999, 1),
            row(1, "2026-03-01", 5310, 1), row(2, "2026-03-01", 3000, 1), row(4, "2026-03-01", 56997, 3),
            row(5, "2026-03-01", 147500, 3), row(7, "2026-03-01", 1325, 1),
        )
    }
}
