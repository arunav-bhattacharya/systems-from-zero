package sfz.stream.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Nested
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import java.sql.Connection
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * Lesson stream-01, exercises 2 and 3, in src/main/kotlin/sfz/stream/l01/ChangeFollower.kt. The
 * services now write only to PostgreSQL; the index follows the database's log.
 */
@Timeout(30, unit = TimeUnit.SECONDS)
class ChangeFollowerTest {

    private val opened = mutableListOf<Connection>()
    private fun connect(): Connection = CdcDb.connect().also { opened += it }

    @BeforeEach
    fun seed() = CdcDb.reset()

    @AfterEach
    fun close() = opened.forEach { runCatching { it.close() } }

    /** An index that was copied from the table, and a slot created right after (no writes in between). */
    private fun followerOfSeed(slot: String = "search_index"): ChangeFollower {
        val db = connect()
        Slot.create(db, slot)
        val index = SearchIndex().apply { CdcDb.seed.forEach(::put) }
        return ChangeFollower(db, slot, index)
    }

    @Nested
    inner class `exercise 2, poll` {

        @Test
        fun `the follower ends where the database ends, even when two clients race`() {
            val follower = followerOfSeed()
            val capture = connect()
            val refund = connect()
            // the same two clients as in exercise 1, but now they only write the database
            CdcDb.exec(capture, "BEGIN", "UPDATE payment SET status = 'CAPTURED' WHERE id = 'pay-981'")
            val waiting = Executors.newSingleThreadExecutor().submit {
                // blocks on pay-981's row lock until capture commits: the database picks the order
                CdcDb.exec(refund, "UPDATE payment SET status = 'REFUNDED' WHERE id = 'pay-981'")
            }
            Thread.sleep(200)
            CdcDb.exec(capture, "COMMIT")
            waiting.get(10, TimeUnit.SECONDS)

            assertThat(follower.poll()).isEqualTo(2)
            assertThat(follower.index.docs.getValue("pay-981").status).isEqualTo("REFUNDED")
            assertThat(follower.index.docs).isEqualTo(CdcDb.rows())
        }

        @Test
        fun `inserts and deletes arrive, rolled-back transactions and other tables don't`() {
            val follower = followerOfSeed()
            val db = connect()
            CdcDb.exec(db, "CREATE TABLE audit_note (id int PRIMARY KEY, note text)")
            CdcDb.exec(
                db,
                "INSERT INTO payment (id, account, amount, status) VALUES ('pay-990', 'acct-99', 15000, 'AUTHORIZED')",
                "DELETE FROM payment WHERE id = 'pay-983'",
                "INSERT INTO audit_note VALUES (1, 'it''s not a payment')",
                "BEGIN",
                "INSERT INTO payment (id, account, amount, status) VALUES ('pay-991', 'acct-99', 1, 'AUTHORIZED')",
                "ROLLBACK",
            )
            try {
                follower.poll()
                assertThat(follower.index.docs.keys).containsExactlyInAnyOrder("pay-981", "pay-982", "pay-990")
                assertThat(follower.index.docs.getValue("pay-990")).isEqualTo(Payment("pay-990", "acct-99", 15000, "AUTHORIZED"))
                assertThat(follower.index.docs).isEqualTo(CdcDb.rows())
            } finally {
                CdcDb.exec(db, "DROP TABLE audit_note")
            }
        }

        @Test
        fun `it applies transactions in commit order and records each commit position once`() {
            val follower = followerOfSeed()
            val db = connect()
            CdcDb.exec(db, "UPDATE payment SET status = 'CAPTURED' WHERE id = 'pay-982'")
            CdcDb.exec(db, "UPDATE payment SET amount = 1300 WHERE id = 'pay-982'")
            assertThat(follower.poll()).isEqualTo(2)
            assertThat(follower.index.applied).hasSize(2)
            assertThat(follower.index.applied).isSorted()
            assertThat(follower.index.appliedLsn).isEqualTo(follower.index.applied.last())
            assertThat(follower.index.docs.getValue("pay-982")).isEqualTo(Payment("pay-982", "acct-42", 1300, "CAPTURED"))
        }

        @Test
        fun `after a confirmed poll the slot has nothing more to give`() {
            val follower = followerOfSeed()
            CdcDb.exec(connect(), "UPDATE payment SET status = 'CAPTURED' WHERE id = 'pay-981'")
            assertThat(follower.poll()).isEqualTo(1)
            assertThat(Slot.peek(connect(), follower.slot)).describedAs("confirmed changes are gone from the slot").isEmpty()
            assertThat(follower.poll()).isEqualTo(0)
        }

        @Test
        fun `a follower that crashed before confirming gets the changes again and skips them`() {
            val index = followerOfSeed().index
            CdcDb.exec(connect(), "UPDATE payment SET status = 'CAPTURED' WHERE id = 'pay-981'")
            CdcDb.exec(connect(), "UPDATE payment SET status = 'REFUNDED' WHERE id = 'pay-981'")

            val first = ChangeFollower(connect(), "search_index", index)
            assertThat(first.poll(confirm = false)).isEqualTo(2)                    // applied, then the process dies
            assertThat(Slot.peek(connect(), "search_index")).describedAs("never confirmed, so PostgreSQL still has them").isNotEmpty()

            val restarted = ChangeFollower(connect(), "search_index", index)       // same index, same bookmark
            assertThat(restarted.poll()).describedAs("both transactions are at or before appliedLsn").isEqualTo(0)
            assertThat(index.applied).doesNotHaveDuplicates().hasSize(2)
            assertThat(Slot.peek(connect(), "search_index")).describedAs("the restarted follower confirmed them").isEmpty()
            assertThat(index.docs).isEqualTo(CdcDb.rows())
        }

        @Test
        fun `a stopped follower falls behind in WAL bytes, and catches up`() {
            val follower = followerOfSeed()
            val db = connect()
            CdcDb.exec(
                db,
                "INSERT INTO payment (id, account, amount, status) " +
                    "SELECT 'bulk-' || g, 'acct-' || (g % 50), g, 'AUTHORIZED' FROM generate_series(1, 3000) g",
            )
            val behind = Slot.lagBytes(db, follower.slot)
            assertThat(behind).describedAs("3,000 inserted rows of WAL not yet confirmed").isGreaterThan(200_000)
            follower.poll()
            assertThat(follower.index.docs).hasSize(3 + 3000)
            assertThat(Slot.lagBytes(db, follower.slot)).describedAs("confirmed up to the last commit").isLessThan(16_384)
        }
    }

    @Nested
    inner class `exercise 3, bootstrap` {

        @Test
        fun `bootstrap copies the rows that existed before the slot`() {
            val follower = ChangeFollower(connect(), "new_index", SearchIndex())
            follower.bootstrap()
            assertThat(follower.index.docs).isEqualTo(CdcDb.rows())
            follower.poll()
            assertThat(follower.index.docs).isEqualTo(CdcDb.rows())
        }

        @Test
        fun `writes committed while the index is being built are not lost`() {
            val follower = ChangeFollower(connect(), "new_index", SearchIndex())
            val traffic = connect()
            follower.bootstrap(afterSlotCreated = {
                CdcDb.exec(
                    traffic,
                    "UPDATE payment SET status = 'REFUNDED' WHERE id = 'pay-981'",
                    "INSERT INTO payment (id, account, amount, status) VALUES ('pay-995', 'acct-17', 700, 'AUTHORIZED')",
                    "DELETE FROM payment WHERE id = 'pay-982'",
                )
            })
            CdcDb.exec(traffic, "UPDATE payment SET status = 'CAPTURED' WHERE id = 'pay-995'")   // after the copy
            follower.poll()
            assertThat(follower.index.docs).isEqualTo(CdcDb.rows())
            assertThat(follower.index.docs.getValue("pay-995").status).isEqualTo("CAPTURED")
            assertThat(follower.index.docs).doesNotContainKey("pay-982")
        }

        @Test
        fun `the slot exists after bootstrap, and it starts no later than the copy`() {
            val db = connect()
            val follower = ChangeFollower(db, "new_index", SearchIndex())
            follower.bootstrap()
            CdcDb.exec(connect(), "UPDATE payment SET amount = 5000 WHERE id = 'pay-981'")
            assertThat(follower.poll()).isEqualTo(1)
            assertThat(follower.index.docs.getValue("pay-981").amount).isEqualTo(5000)
        }
    }
}
