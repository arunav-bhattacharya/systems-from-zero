package sfz.nosql.l10

import com.mongodb.client.model.Filters
import com.mongodb.client.model.Updates
import org.assertj.core.api.Assertions.assertThat
import org.bson.Document
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.TestInstance
import sfz.nosql.support.TestMongoReplicaSet
import java.util.concurrent.Callable
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class MongoTransfersTest {
    @BeforeAll
    fun start() {
        TestMongoReplicaSet.client // starts the one-member replica set (a few seconds, more on the first pull)
    }

    /** A database of its own with A-1001 = 100.00 and A-2002 = 50.00. */
    private fun fresh(): MongoTransfers {
        val db = TestMongoReplicaSet.freshDatabase("l10")
        val t = MongoTransfers(TestMongoReplicaSet.client, db)
        t.accounts.insertMany(listOf(Document("_id", "A-1001").append("balanceMinor", 10_000L), Document("_id", "A-2002").append("balanceMinor", 5_000L)))
        db.createCollection("ledger") // collections can't be created inside a transaction on every version
        return t
    }

    private fun MongoTransfers.balance(id: String): Long = accounts.find(Filters.eq("_id", id)).first()!!.getLong("balanceMinor")

    @Test
    fun `a transfer moves the money and writes one ledger entry, in one attempt`() {
        val t = fresh()
        assertThat(t.transfer("txf-1", "A-1001", "A-2002", 3_000)).isEqualTo(TransferResult.Done(1))
        assertThat(t.balance("A-1001")).isEqualTo(7_000)
        assertThat(t.balance("A-2002")).isEqualTo(8_000)
        assertThat(t.ledger.find(Filters.eq("_id", "txf-1")).first()!!.getLong("amountMinor")).isEqualTo(3_000)
    }

    @Test
    fun `not enough money aborts everything, the ledger entry included`() {
        val t = fresh()
        assertThat(t.transfer("txf-2", "A-1001", "A-2002", 50_000)).isEqualTo(TransferResult.InsufficientFunds)
        assertThat(t.balance("A-1001")).isEqualTo(10_000)
        assertThat(t.balance("A-2002")).isEqualTo(5_000)
        assertThat(t.ledger.countDocuments()).isZero()
    }

    @Test
    fun `the same transfer id twice moves the money once`() {
        val t = fresh()
        t.transfer("txf-3", "A-1001", "A-2002", 3_000)
        // the retry comes after the money ran low: it must still say "already done", not "insufficient"
        t.accounts.updateOne(Filters.eq("_id", "A-1001"), Updates.set("balanceMinor", 1_000L))
        assertThat(t.transfer("txf-3", "A-1001", "A-2002", 3_000)).isEqualTo(TransferResult.AlreadyDone)
        assertThat(t.balance("A-2002")).isEqualTo(8_000)
        assertThat(t.ledger.countDocuments()).isEqualTo(1)
    }

    @Test
    fun `a write conflict with another transaction is retried until that transaction commits`() {
        val t = fresh()
        // another transaction changes A-1001 and stays open for 300 ms
        val other = TestMongoReplicaSet.client.startSession()
        other.startTransaction(t.options)
        t.accounts.updateOne(other, Filters.eq("_id", "A-1001"), Updates.inc("balanceMinor", -1_000L))

        val pool = Executors.newSingleThreadExecutor()
        val result = pool.submit(Callable { t.transfer("txf-4", "A-1001", "A-2002", 3_000) })
        Thread.sleep(300)
        other.commitTransaction()
        other.close()

        val done = result.get(20, TimeUnit.SECONDS)
        pool.shutdown()
        assertThat(done).isInstanceOf(TransferResult.Done::class.java)
        assertThat((done as TransferResult.Done).attempts).`as`("the first attempts must hit WriteConflict and start over").isGreaterThan(1)
        // the retry ran on a fresh snapshot, so it saw the other transaction's debit
        assertThat(t.balance("A-1001")).isEqualTo(6_000)
        assertThat(t.balance("A-2002")).isEqualTo(8_000)
    }

    @Test
    fun `twenty concurrent transfers on one hot account conserve the money`() {
        val t = fresh()
        val pool = Executors.newFixedThreadPool(10)
        val start = CountDownLatch(1)
        // ten each way, 5.00 at a time: every one fits, so every one must commit
        val jobs = (1..20).map { i ->
            pool.submit(Callable {
                start.await()
                if (i % 2 == 0) t.transfer("txf-c$i", "A-1001", "A-2002", 500) else t.transfer("txf-c$i", "A-2002", "A-1001", 500)
            })
        }
        start.countDown()
        val results = jobs.map { it.get(30, TimeUnit.SECONDS) }
        pool.shutdown()
        assertThat(results).allMatch { it is TransferResult.Done }
        assertThat(t.balance("A-1001") + t.balance("A-2002")).isEqualTo(15_000)
        assertThat(t.balance("A-1001")).isEqualTo(10_000)
        assertThat(t.ledger.countDocuments()).isEqualTo(20)
    }
}
