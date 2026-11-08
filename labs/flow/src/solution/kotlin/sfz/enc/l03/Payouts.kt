package sfz.enc.l03

import java.math.BigDecimal
import java.sql.Connection
import java.util.concurrent.atomic.AtomicInteger

/**
 * The payout service moves `payouts.amount` (numeric euros, 40.00) to `payouts.amount_minor` (bigint cents, 4000)
 * with an expand/contract migration. Four versions of the service run in turn, two at a time during each rollout:
 *
 * | version | writes                 | reads        |
 * |---------|------------------------|--------------|
 * | v1      | amount                 | amount       |
 * | v2      | amount and amount_minor| amount       |
 * | v3      | amount and amount_minor| amount_minor (and compares it with amount: a shadow read) |
 * | v4      | amount_minor           | amount_minor |
 *
 * The table at the start: `payouts(id bigint primary key, merchant text not null, amount numeric(12,2) not null)`.
 */
interface PayoutApp {
    /** Inserts the payout, or updates it if the id exists. */
    fun save(conn: Connection, id: Long, merchant: String, amountMinor: Long)

    /** The payout's amount in cents, or null if there's no such payout. */
    fun amountMinorOf(conn: Connection, id: Long): Long?
}

/** Cents to euros: 4000 -> 40.00. */
fun euros(amountMinor: Long): BigDecimal = BigDecimal.valueOf(amountMinor, 2)

private fun readLong(conn: Connection, sql: String, id: Long): Long? =
    conn.prepareStatement(sql).use { st ->
        st.setLong(1, id)
        st.executeQuery().use { rs -> if (rs.next()) rs.getLong(1).takeUnless { rs.wasNull() } else null }
    }

/** Version 1: only knows `amount`. Complete. */
object PayoutsV1 : PayoutApp {
    override fun save(conn: Connection, id: Long, merchant: String, amountMinor: Long) {
        conn.prepareStatement(
            """INSERT INTO payouts (id, merchant, amount) VALUES (?, ?, ?)
               ON CONFLICT (id) DO UPDATE SET merchant = excluded.merchant, amount = excluded.amount"""
        ).use { st ->
            st.setLong(1, id); st.setString(2, merchant); st.setBigDecimal(3, euros(amountMinor))
            st.executeUpdate()
        }
    }

    override fun amountMinorOf(conn: Connection, id: Long): Long? =
        readLong(conn, "SELECT (amount * 100)::bigint FROM payouts WHERE id = ?", id)
}

/** Version 2: writes both columns, still reads `amount`. */
object PayoutsV2 : PayoutApp {
    /**
     * Dual write: the same upsert as v1, plus `amount_minor`, in ONE statement so both columns always change together.
     * On conflict, update `merchant`, `amount` and `amount_minor`.
     */
    override fun save(conn: Connection, id: Long, merchant: String, amountMinor: Long) {
        // one statement, so the two columns can never disagree after a v2 write
        conn.prepareStatement(
            """INSERT INTO payouts (id, merchant, amount, amount_minor) VALUES (?, ?, ?, ?)
               ON CONFLICT (id) DO UPDATE SET merchant = excluded.merchant, amount = excluded.amount,
                                              amount_minor = excluded.amount_minor"""
        ).use { st ->
            st.setLong(1, id); st.setString(2, merchant); st.setBigDecimal(3, euros(amountMinor)); st.setLong(4, amountMinor)
            st.executeUpdate()
        }
    }

    override fun amountMinorOf(conn: Connection, id: Long): Long? = PayoutsV1.amountMinorOf(conn, id)
}

/** Version 3: reads `amount_minor`, and checks it against `amount` on every read. Complete. */
object PayoutsV3 : PayoutApp {
    /**
     * Reads where the new column disagreed with the old one. It is the check for the read switch (phase 2):
     * once v4 starts writing only `amount_minor`, `amount` goes stale on purpose and this count means nothing.
     */
    val mismatches = AtomicInteger()

    override fun save(conn: Connection, id: Long, merchant: String, amountMinor: Long) = PayoutsV2.save(conn, id, merchant, amountMinor)

    override fun amountMinorOf(conn: Connection, id: Long): Long? =
        conn.prepareStatement("SELECT amount_minor, (amount * 100)::bigint FROM payouts WHERE id = ?").use { st ->
            st.setLong(1, id)
            st.executeQuery().use { rs ->
                if (!rs.next()) return null
                val new = rs.getLong(1).takeUnless { rs.wasNull() }
                val old = rs.getLong(2).takeUnless { rs.wasNull() }
                if (old != null && new != old) mismatches.incrementAndGet() // the shadow read: log it, serve the new value
                new
            }
        }
}

/** Version 4: only `amount_minor`. It never mentions `amount`, so the contract step can drop that column under it. Complete. */
object PayoutsV4 : PayoutApp {
    override fun save(conn: Connection, id: Long, merchant: String, amountMinor: Long) {
        conn.prepareStatement(
            """INSERT INTO payouts (id, merchant, amount_minor) VALUES (?, ?, ?)
               ON CONFLICT (id) DO UPDATE SET merchant = excluded.merchant, amount_minor = excluded.amount_minor"""
        ).use { st ->
            st.setLong(1, id); st.setString(2, merchant); st.setLong(3, amountMinor)
            st.executeUpdate()
        }
    }

    override fun amountMinorOf(conn: Connection, id: Long): Long? =
        readLong(conn, "SELECT amount_minor FROM payouts WHERE id = ?", id)
}

/** The schema changes. Each one is its own migration (Flyway V3, V4, ...) and runs between two rollouts. */
object Migration {
    /** Expand: add `amount_minor` as a nullable bigint, so v1's inserts, which don't mention it, keep working. */
    fun expand(conn: Connection) {
        // nullable and no default: a catalog change only, no table rewrite, and old INSERTs still work
        conn.createStatement().use { it.execute("ALTER TABLE payouts ADD COLUMN amount_minor bigint") }
    }

    /**
     * Backfill one batch: set `amount_minor = round(amount * 100)::bigint` on at most [limit] rows where it is NULL
     * or differs from that value, lowest ids first. (It can differ: a v1 instance may have changed `amount` after a
     * v2 instance wrote both columns.) Returns how many rows it changed, so the caller can loop until it returns 0.
     * Small batches keep each transaction's row locks and WAL small while the service keeps running.
     */
    fun backfillBatch(conn: Connection, limit: Int): Int =
        conn.prepareStatement(
            """UPDATE payouts SET amount_minor = round(amount * 100)::bigint
               WHERE id IN (SELECT id FROM payouts
                            WHERE amount_minor IS DISTINCT FROM round(amount * 100)::bigint -- NULL, or stale
                            ORDER BY id LIMIT ?)"""
        ).use { st ->
            st.setInt(1, limit)
            st.executeUpdate() // each call is its own short transaction in autocommit mode
        }

    /**
     * Before v4 rolls out: v4 doesn't write `amount`, so it must allow NULL, and `amount_minor` can now be NOT NULL.
     * PostgreSQL 18 lets a NOT NULL constraint be added NOT VALID (no scan, brief lock) and validated separately
     * (a scan under a weaker lock that lets reads and writes continue). Complete.
     */
    fun prepareSwitchWrites(conn: Connection) {
        conn.createStatement().use { st ->
            st.execute("ALTER TABLE payouts ALTER COLUMN amount DROP NOT NULL")
            st.execute("ALTER TABLE payouts ADD CONSTRAINT payouts_amount_minor_not_null NOT NULL amount_minor NOT VALID")
            st.execute("ALTER TABLE payouts VALIDATE CONSTRAINT payouts_amount_minor_not_null")
        }
    }

    /** Contract: once no running version reads or writes `amount`, drop it. */
    fun contract(conn: Connection) {
        // only after the last v3 is gone: v1, v2 and v3 would all fail without this column
        conn.createStatement().use { it.execute("ALTER TABLE payouts DROP COLUMN amount") }
    }
}
