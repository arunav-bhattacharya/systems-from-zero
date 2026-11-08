package sfz.txn.l04

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.txn.l04.Isolation.READ_COMMITTED
import sfz.txn.l04.Isolation.REPEATABLE_READ

class MvccStoreTest {
    private val db = MvccStore()

    /** Runs [block] in its own transaction and commits it. */
    private fun <T> autocommit(block: (Tx) -> T): T {
        val tx = db.begin()
        val result = block(tx)
        db.commit(tx)
        return result
    }

    private fun set(key: String, value: Long) = autocommit { db.put(it, key, value) }
    private fun read(key: String): Long? = autocommit { db.get(it, key) }

    @Test
    fun `a reader's snapshot stays the same while a writer commits`() {
        set("acct-1", 50_000)
        val report = db.begin(REPEATABLE_READ)
        assertThat(db.get(report, "acct-1")).isEqualTo(50_000)
        val transfer = db.begin()
        db.put(transfer, "acct-1", 47_500)
        db.commit(transfer)
        assertThat(db.get(report, "acct-1")).`as`("the report, after the transfer committed").isEqualTo(50_000)
        assertThat(read("acct-1")).`as`("a transaction that starts after the commit").isEqualTo(47_500)
        assertThat(db.versions("acct-1")).`as`("both versions are kept").hasSize(2)
    }

    @Test
    fun `a transaction sees its own writes and nobody else does until it commits`() {
        set("acct-1", 100)
        val tx = db.begin()
        db.put(tx, "acct-1", 70)
        db.put(tx, "acct-2", 30)
        assertThat(db.get(tx, "acct-1")).`as`("its own update").isEqualTo(70)
        assertThat(db.get(tx, "acct-2")).`as`("its own insert").isEqualTo(30)
        assertThat(read("acct-1")).`as`("another transaction, before the commit").isEqualTo(100)
        assertThat(read("acct-2")).`as`("another transaction, before the commit").isNull()
        db.commit(tx)
        assertThat(read("acct-1")).isEqualTo(70)
        assertThat(read("acct-2")).isEqualTo(30)
    }

    @Test
    fun `the visibility rule uses the snapshot, not the commit log alone`() {
        val writer = db.begin()
        db.put(writer, "acct-1", 10)
        val reader = db.begin()
        db.commit(writer)
        assertThat(db.status(writer.id)).isEqualTo(TxStatus.COMMITTED)
        assertThat(reader.snapshot.active).`as`("the reader's snapshot lists the writer as running").contains(writer.id)
        assertThat(db.sees(reader.snapshot, writer.id)).`as`("committed, but after the reader's snapshot").isFalse()
        assertThat(db.get(reader, "acct-1")).isNull()
        val later = db.begin()
        assertThat(db.sees(later.snapshot, writer.id)).isTrue()
        assertThat(db.sees(later.snapshot, later.id)).`as`("a transaction always sees itself").isTrue()
        assertThat(db.sees(reader.snapshot, later.id)).`as`("a transaction that started after the snapshot").isFalse()
    }

    @Test
    fun `read committed takes a new snapshot for every statement, repeatable read keeps one`() {
        set("acct-1", 500)
        val rc = db.begin(READ_COMMITTED)
        val rr = db.begin(REPEATABLE_READ)
        assertThat(db.get(rc, "acct-1")).isEqualTo(500)
        assertThat(db.get(rr, "acct-1")).isEqualTo(500)
        set("acct-1", 400)
        assertThat(db.get(rc, "acct-1")).`as`("read committed, next statement").isEqualTo(400)
        assertThat(db.get(rr, "acct-1")).`as`("repeatable read, next statement").isEqualTo(500)
    }

    @Test
    fun `an aborted transaction's versions are never visible`() {
        set("acct-1", 900)
        val tx = db.begin()
        db.put(tx, "acct-1", 0)
        db.put(tx, "acct-9", 900)
        db.delete(tx, "acct-1")
        db.abort(tx)
        assertThat(read("acct-1")).isEqualTo(900)
        assertThat(read("acct-9")).isNull()
        assertThat(db.versions("acct-1").first().xmax).`as`("the aborted id is still written in xmax").isEqualTo(tx.id)
    }

    @Test
    fun `delete hides the row from later snapshots, not from older ones`() {
        set("acct-1", 250)
        val old = db.begin()
        val tx = db.begin()
        assertThat(db.delete(tx, "acct-1")).isTrue()
        assertThat(db.get(tx, "acct-1")).`as`("the deleter").isNull()
        db.commit(tx)
        assertThat(db.get(old, "acct-1")).`as`("a snapshot taken before the delete").isEqualTo(250)
        assertThat(read("acct-1")).`as`("a snapshot taken after").isNull()
        assertThat(db.versions("acct-1")).`as`("a delete only sets xmax: no new version").hasSize(1)
        assertThat(autocommit { db.delete(it, "acct-1") }).`as`("deleting it again").isFalse()
    }

    @Test
    fun `the second writer of a row fails while the first is still running`() {
        set("acct-1", 1_000)
        val first = db.begin()
        db.put(first, "acct-1", 900)
        val second = db.begin(READ_COMMITTED)
        assertThatThrownBy { db.put(second, "acct-1", 1_100) }.isInstanceOf(WriteConflict::class.java)
        db.abort(second)
        val third = db.begin()
        assertThatThrownBy { db.delete(third, "acct-1") }.`as`("a delete conflicts too").isInstanceOf(WriteConflict::class.java)
        db.abort(third)
        db.commit(first)
        set("acct-1", 1_100)                        // a transaction that starts after the commit may write
        assertThat(read("acct-1")).isEqualTo(1_100)
    }

    @Test
    fun `a repeatable read writer fails if the row changed after its snapshot, read committed does not`() {
        set("acct-1", 1_000)
        val rr = db.begin(REPEATABLE_READ)
        val rc = db.begin(READ_COMMITTED)
        assertThat(db.get(rr, "acct-1")).isEqualTo(1_000)
        assertThat(db.get(rc, "acct-1")).isEqualTo(1_000)
        set("acct-1", 900)                          // someone else commits a change
        assertThatThrownBy { db.put(rr, "acct-1", 1_000 + 50) }.isInstanceOf(WriteConflict::class.java)
        db.put(rc, "acct-1", db.get(rc, "acct-1")!! + 50)
        db.commit(rc)
        assertThat(read("acct-1")).`as`("read committed applied +50 to the newest version").isEqualTo(950)
    }

    @Test
    fun `a writer may overwrite a row whose last writer aborted`() {
        set("acct-1", 300)
        val loser = db.begin()
        db.put(loser, "acct-1", 0)
        db.abort(loser)
        val tx = db.begin()
        db.put(tx, "acct-1", 200)
        db.commit(tx)
        assertThat(read("acct-1")).isEqualTo(200)
    }

    @Test
    fun `write skew - snapshot isolation lets two withdrawals break a shared limit`() {
        // rule: the two cards of one account may go negative, but their sum must stay >= 0
        set("card-1", 7_500)
        set("card-2", 7_500)
        val a = db.begin()
        val b = db.begin()
        for ((tx, card) in listOf(a to "card-1", b to "card-2")) {
            val sum = db.get(tx, "card-1")!! + db.get(tx, "card-2")!!
            assertThat(sum).`as`("each sees the sum before both withdrawals").isEqualTo(15_000)
            db.put(tx, card, db.get(tx, card)!! - 10_000)   // each writes a different row: no write conflict
        }
        db.commit(a)
        db.commit(b)
        assertThat(read("card-1")!! + read("card-2")!!).`as`("the sum after both commit").isEqualTo(-5_000)
    }

    @Test
    fun `vacuum removes only the versions no snapshot can see`() {
        set("acct-1", 100)
        set("acct-1", 200)
        set("acct-1", 300)
        set("acct-2", 5)
        assertThat(db.versionCount()).isEqualTo(4)
        assertThat(db.vacuum()).`as`("versions removed").isEqualTo(2)
        assertThat(db.versions("acct-1").map { it.value }).containsExactly(300L)
        assertThat(read("acct-1")).isEqualTo(300)
        assertThat(read("acct-2")).isEqualTo(5)
        set("acct-2", 6)
        autocommit { db.delete(it, "acct-1") }
        assertThat(db.vacuum()).isEqualTo(2)
        assertThat(db.versions("acct-1")).`as`("a deleted row, vacuumed").isEmpty()
        assertThat(db.versionCount()).isEqualTo(1)
    }

    @Test
    fun `a long-running reader holds vacuum back`() {
        set("acct-1", 1)
        val report = db.begin()
        assertThat(db.get(report, "acct-1")).isEqualTo(1)
        for (v in 2L..6L) set("acct-1", v)
        assertThat(db.horizon()).`as`("the horizon is the report's snapshot xmin").isEqualTo(report.snapshot.xmin)
        // versions 2 to 5 are invisible to everyone, but they were deleted after the horizon, so they stay too:
        // one old snapshot holds back every version that died after it was taken, as in PostgreSQL
        assertThat(db.vacuum()).`as`("removed while the report is open").isEqualTo(0)
        assertThat(db.versions("acct-1")).hasSize(6)
        assertThat(db.get(report, "acct-1")).isEqualTo(1)
        db.commit(report)
        assertThat(db.vacuum()).`as`("removed once the report ended").isEqualTo(5)
        assertThat(db.versions("acct-1").map { it.value }).containsExactly(6L)
    }

    @Test
    fun `vacuum removes the versions of aborted transactions, and nothing a running writer needs`() {
        set("acct-1", 40)
        val loser = db.begin()
        db.put(loser, "acct-1", 41)
        db.put(loser, "acct-7", 7)
        db.abort(loser)
        val open = db.begin()
        db.put(open, "acct-1", 42)
        assertThat(db.vacuum()).`as`("the two aborted versions").isEqualTo(2)
        assertThat(db.versions("acct-7")).isEmpty()
        assertThat(db.versions("acct-1").map { it.value }).`as`("the committed one and the running writer's").containsExactly(40L, 42L)
        db.commit(open)
        assertThat(read("acct-1")).isEqualTo(42)
    }
}
