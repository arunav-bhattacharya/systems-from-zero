package sfz.stream.l01

import java.sql.Connection

/**
 * Lesson stream-01, exercises 2 and 3: make the search index a follower of the database. Instead
 * of writing to the index, the services write only to PostgreSQL, and this follower reads the
 * committed changes from a logical replication slot and applies them to the index in commit order.
 *
 * Use the given helpers in Given.kt: [Slot] (create, peek, confirm), [TestDecoding.parse] and the
 * index's [SearchIndex.appliedLsn] / [SearchIndex.markApplied].
 *
 * Check it: ./gradlew :sql:test --tests 'sfz.stream.l01.*'   (from the labs folder)
 */
class ChangeFollower(private val db: Connection, val slot: String, val index: SearchIndex) {

    /**
     * Exercise 2. Reads every change waiting in the slot ([Slot.peek]) and applies each committed
     * transaction to the index, in the order the slot returns them:
     *
     * - Collect the `public.payment` rows between a BEGIN and its COMMIT. Ignore other tables.
     * - At the COMMIT, the row's LSN is the transaction's commit position. If it is not after
     *   [SearchIndex.appliedLsn], the index already has this transaction (the slot sent it again
     *   after a crash): skip it. Otherwise apply its rows (INSERT and UPDATE put a [Payment] built
     *   from the columns `id`, `account`, `amount`, `status`; DELETE removes the document whose id
     *   is in the columns) and call [SearchIndex.markApplied] with the commit LSN.
     * - If [confirm] is true and you saw at least one COMMIT, confirm the last COMMIT's LSN with
     *   [Slot.confirm], so the slot forgets what the index now has. The tests pass false to act out
     *   a follower that crashes after applying and before confirming.
     *
     * Returns how many transactions were applied (skipped ones don't count).
     */
    fun poll(confirm: Boolean = true): Int {
        TODO("exercise 2: peek, apply committed transactions after appliedLsn, confirm")
    }

    /**
     * Exercise 3. Gives a new, empty index its first copy of the table, without losing any write that
     * happens meanwhile:
     *
     * 1. create the slot ([Slot.create]), so every change committed from now on is kept for you;
     * 2. call [afterSlotCreated] (the tests use it to commit writes from another connection at exactly
     *    this point, as live traffic would);
     * 3. copy every row of `payment` into the index with one SELECT.
     *
     * Changes committed between steps 1 and 3 end up both in the copy and in the slot. The next
     * [poll] applies them again, which is harmless: each change carries the whole row.
     */
    fun bootstrap(afterSlotCreated: () -> Unit = {}) {
        TODO("exercise 3: create the slot, call the hook, copy the table")
    }
}
