package sfz.stream.l01

import java.sql.Connection
import java.util.concurrent.ConcurrentHashMap

/**
 * Lesson stream-01: everything in this file is given. Your exercises are in DualWrite.kt and
 * ChangeFollower.kt.
 *
 * The system of record is PostgreSQL's `payment` table:
 *
 *   payment(id text PRIMARY KEY, account text, amount bigint, status text, created_at timestamptz)
 *
 * The derived system is [SearchIndex], an in-memory stand-in for the search index the support team
 * queries ("show me every REFUNDED payment for acct-17").
 */

/** One payment as the search index stores it. */
data class Payment(val id: String, val account: String, val amount: Long, val status: String)

/**
 * The search index (given). It holds one document per payment id. When the index follows the
 * database through change data capture, it also keeps its bookmark: [appliedLsn], the commit
 * position of the last transaction it applied, and [applied], every commit position it applied, in
 * order. A real index would store the bookmark next to its documents, so both survive a restart.
 */
class SearchIndex {
    val docs: MutableMap<String, Payment> = ConcurrentHashMap()

    @Volatile
    var appliedLsn: Long = 0
        private set

    val applied: MutableList<Long> = mutableListOf()

    fun put(p: Payment) {
        docs[p.id] = p
    }

    fun delete(id: String) {
        docs.remove(id)
    }

    /** What a dual write does: change one field of a document the service already has. */
    fun setStatus(id: String, status: String) {
        docs.compute(id) { _, old -> old?.copy(status = status) ?: error("no document $id in the index") }
    }

    /** Records that the transaction that committed at [lsn] has been applied. */
    fun markApplied(lsn: Long) {
        check(lsn > appliedLsn) { "commit LSN ${Lsn.format(lsn)} is not after ${Lsn.format(appliedLsn)}" }
        appliedLsn = lsn
        applied += lsn
    }
}

/** PostgreSQL log sequence numbers: `0/1C0CAE0` is the 64-bit WAL position 0x1C0CAE0. */
object Lsn {
    fun parse(text: String): Long {
        val (hi, lo) = text.split("/")
        return (hi.toLong(16) shl 32) or lo.toLong(16)
    }

    fun format(lsn: Long): String = "%X/%X".format(lsn ushr 32, lsn and 0xFFFFFFFFL)
}

/** One row of `pg_logical_slot_peek_changes`: the WAL position, the transaction id and the decoded text. */
data class RawChange(val lsn: Long, val xid: Long, val data: String)

/**
 * A logical replication slot, driven through PostgreSQL's SQL functions (given). The slot decodes
 * the WAL with the built-in `test_decoding` plugin, which prints each change as a line of text.
 */
object Slot {
    /** Creates the slot and returns the WAL position from which it will decode. */
    fun create(db: Connection, slot: String): Long =
        db.prepareStatement("SELECT lsn::text FROM pg_create_logical_replication_slot(?, 'test_decoding')").use { st ->
            st.setString(1, slot)
            st.executeQuery().use { rs -> rs.next(); Lsn.parse(rs.getString(1)) }
        }

    /**
     * Every committed change the slot has not been told to forget, in commit order, one transaction
     * after another (BEGIN, its rows, COMMIT). Peeking consumes nothing: call it twice and you get
     * the same rows twice, which is what a consumer sees after a crash before it confirmed.
     */
    fun peek(db: Connection, slot: String): List<RawChange> =
        db.prepareStatement("SELECT lsn::text, xid::text::bigint, data FROM pg_logical_slot_peek_changes(?, NULL, NULL)").use { st ->
            st.setString(1, slot)
            st.executeQuery().use { rs ->
                buildList { while (rs.next()) add(RawChange(Lsn.parse(rs.getString(1)), rs.getLong(2), rs.getString(3))) }
            }
        }

    /**
     * Confirms everything up to and including the transaction whose COMMIT row had [lsn]. The slot
     * won't return those changes again, and PostgreSQL may recycle the WAL they lived in.
     */
    fun confirm(db: Connection, slot: String, lsn: Long) {
        db.prepareStatement("SELECT pg_replication_slot_advance(?, ?::pg_lsn)").use { st ->
            st.setString(1, slot)
            st.setString(2, Lsn.format(lsn))
            st.executeQuery().close()
        }
    }

    /** Bytes of WAL written since the slot's last confirmed position: how far the consumer is behind. */
    fun lagBytes(db: Connection, slot: String): Long =
        db.prepareStatement(
            "SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)::bigint FROM pg_replication_slots WHERE slot_name = ?",
        ).use { st ->
            st.setString(1, slot)
            st.executeQuery().use { rs -> check(rs.next()) { "no slot $slot" }; rs.getLong(1) }
        }

    fun drop(db: Connection, slot: String) {
        db.prepareStatement("SELECT pg_drop_replication_slot(?)").use { st ->
            st.setString(1, slot)
            st.executeQuery().close()
        }
    }
}

/** One line of `test_decoding` output, parsed (given). */
sealed interface Decoded {
    data class Begin(val xid: Long) : Decoded
    data class Commit(val xid: Long) : Decoded

    /** An INSERT, UPDATE or DELETE of one row. A DELETE carries only the key columns. */
    data class Row(val table: String, val op: String, val columns: Map<String, String?>) : Decoded
}

object TestDecoding {
    private val ROW = Regex("""^table ([^:]+): (INSERT|UPDATE|DELETE): (.*)$""")

    // name[type]:value, where value is 'quoted with '' for a quote', or a bare token (a number, null, true)
    private val COLUMN = Regex("""([^\s\[]+)\[([^\]]+)\]:('(?:[^']|'')*'|\S+)""")

    fun parse(line: String): Decoded {
        if (line.startsWith("BEGIN")) return Decoded.Begin(line.removePrefix("BEGIN").trim().toLong())
        if (line.startsWith("COMMIT")) return Decoded.Commit(line.removePrefix("COMMIT").trim().toLong())
        val m = ROW.matchEntire(line) ?: error("not a test_decoding line: $line")
        val (table, op, rest) = m.destructured
        val columns = COLUMN.findAll(rest).associate { c ->
            val raw = c.groupValues[3]
            c.groupValues[1] to when {
                raw == "null" -> null
                raw.startsWith("'") -> raw.substring(1, raw.length - 1).replace("''", "'")
                else -> raw
            }
        }
        return Decoded.Row(table, op, columns)
    }
}
