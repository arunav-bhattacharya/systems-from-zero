package sfz.stream.l01

import java.sql.Connection

/**
 * Lesson stream-01, exercises 2 and 3: the search index as a follower of PostgreSQL's log.
 *
 * Check it: ./gradlew :sql:solutionTest --tests 'sfz.stream.l01.*'   (from the labs folder)
 */
class ChangeFollower(private val db: Connection, val slot: String, val index: SearchIndex) {

    /** Exercise 2: apply each committed transaction once, in commit order, then confirm. */
    fun poll(confirm: Boolean = true): Int {
        val rows = mutableListOf<Decoded.Row>()   // the current transaction's payment rows
        var applied = 0
        var lastCommit = 0L
        for (change in Slot.peek(db, slot)) {
            when (val d = TestDecoding.parse(change.data)) {
                is Decoded.Begin -> rows.clear()
                is Decoded.Row -> if (d.table == "public.payment") rows += d
                is Decoded.Commit -> {
                    // the COMMIT row's LSN is the transaction's position in the database's one order
                    if (change.lsn > index.appliedLsn) {
                        rows.forEach(::apply)
                        index.markApplied(change.lsn)        // the bookmark moves with the data
                        applied++
                    }                                        // else: sent again after a crash, already applied
                    lastCommit = change.lsn
                    rows.clear()
                }
            }
        }
        // only now may PostgreSQL forget these changes; a crash before this line means they come back
        if (confirm && lastCommit > 0) Slot.confirm(db, slot, lastCommit)
        return applied
    }

    private fun apply(row: Decoded.Row) {
        val c = row.columns
        when (row.op) {
            "INSERT", "UPDATE" -> index.put(Payment(c.getValue("id")!!, c.getValue("account")!!, c.getValue("amount")!!.toLong(), c.getValue("status")!!))
            "DELETE" -> index.delete(c.getValue("id")!!)   // a delete carries the key only
        }
    }

    /** Exercise 3: slot first, copy second, so nothing committed in between is lost. */
    fun bootstrap(afterSlotCreated: () -> Unit = {}) {
        Slot.create(db, slot)          // from here on, PostgreSQL keeps every committed change for us
        afterSlotCreated()             // live traffic keeps writing
        db.createStatement().use { st ->
            st.executeQuery("SELECT id, account, amount, status FROM payment").use { rs ->
                while (rs.next()) index.put(Payment(rs.getString(1), rs.getString(2), rs.getLong(3), rs.getString(4)))
            }
        }
        // the copy may already include changes that are also waiting in the slot; poll() reapplies them,
        // and since each change carries the whole row, the index ends where the table is
    }
}
