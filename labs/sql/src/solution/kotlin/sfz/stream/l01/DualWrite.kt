package sfz.stream.l01

import java.sql.Connection
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import kotlin.concurrent.thread

/**
 * Lesson stream-01, exercise 1 of 3: make the dual-write race happen on purpose.
 *
 * Check it: ./gradlew :sql:solutionTest --tests 'sfz.stream.l01.*'   (from the labs folder)
 */
object DualWrite {

    /** What the payment service does today (given): database first, then the index. */
    fun setStatus(db: Connection, index: SearchIndex, id: String, status: String, between: () -> Unit = {}) {
        db.prepareStatement("UPDATE payment SET status = ? WHERE id = ?").use { st ->
            st.setString(1, status)
            st.setString(2, id)
            check(st.executeUpdate() == 1) { "no payment $id" }
        }
        between()
        index.setStatus(id, status)
    }

    /** Exercise 1: capture's database write, refund's two writes, then capture's index write. */
    fun race(capture: Connection, refund: Connection, index: SearchIndex, id: String) {
        val captureInDb = CountDownLatch(1)   // step 1 done: refund may start
        val refundDone = CountDownLatch(1)    // steps 2 and 3 done: capture may write the index
        val failure = AtomicReference<Throwable?>(null)

        val captureClient = thread(name = "capture") {
            runCatching {
                setStatus(capture, index, id, "CAPTURED", between = {
                    captureInDb.countDown()                                   // committed CAPTURED in PostgreSQL
                    check(refundDone.await(10, TimeUnit.SECONDS)) { "refund never finished" }
                })                                                            // then writes CAPTURED to the index: last
            }.onFailure { failure.compareAndSet(null, it); captureInDb.countDown() }
        }
        val refundClient = thread(name = "refund") {
            runCatching {
                check(captureInDb.await(10, TimeUnit.SECONDS)) { "capture never wrote the database" }
                setStatus(refund, index, id, "REFUNDED")                     // database, then index: both REFUNDED
            }.onFailure { failure.compareAndSet(null, it) }
            refundDone.countDown()
        }
        captureClient.join()
        refundClient.join()
        failure.get()?.let { throw it }
        // Nothing failed. PostgreSQL saw CAPTURED then REFUNDED; the index saw REFUNDED then CAPTURED.
    }
}
