package sfz.stream.l01

import java.sql.Connection

/**
 * Lesson stream-01, exercise 1 of 3: make the dual-write race happen on purpose.
 *
 * Check it: ./gradlew :sql:test --tests 'sfz.stream.l01.*'   (from the labs folder)
 */
object DualWrite {

    /**
     * What the payment service does today (given): it writes the new status to PostgreSQL (the
     * connection is in autocommit mode, so the UPDATE is committed when it returns), then writes the
     * same status to the search index. [between] runs after the database write and before the index
     * write; the race below uses it to pause one client at exactly that point.
     */
    fun setStatus(db: Connection, index: SearchIndex, id: String, status: String, between: () -> Unit = {}) {
        db.prepareStatement("UPDATE payment SET status = ? WHERE id = ?").use { st ->
            st.setString(1, status)
            st.setString(2, id)
            check(st.executeUpdate() == 1) { "no payment $id" }
        }
        between()
        index.setStatus(id, status)
    }

    /**
     * Exercise 1. Two clients change payment [id] at the same moment: the capture client sets it to
     * CAPTURED through connection [capture], the refund client sets it to REFUNDED through
     * connection [refund]. Each calls [setStatus]. Run them on two threads and force this order with
     * latches (java.util.concurrent.CountDownLatch):
     *
     *   1. capture writes the database (CAPTURED)
     *   2. refund writes the database (REFUNDED)
     *   3. refund writes the index (REFUNDED)
     *   4. capture writes the index (CAPTURED)
     *
     * Wait for both threads, and rethrow anything either of them threw. Both clients succeed, no
     * exception is thrown, and the two stores end up different.
     */
    fun race(capture: Connection, refund: Connection, index: SearchIndex, id: String) {
        TODO("exercise 1: run the two clients on two threads in the order above")
    }
}
