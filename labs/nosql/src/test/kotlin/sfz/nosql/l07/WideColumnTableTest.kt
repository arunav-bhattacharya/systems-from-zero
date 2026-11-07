package sfz.nosql.l07

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test

class WideColumnTableTest {
    // PRIMARY KEY ((account_id), created_at, payment_id): AP1, an account's payments in time order
    private fun byAccount() = WideColumnTable(PrimaryKey(listOf("account_id"), listOf("created_at", "payment_id")))

    // PRIMARY KEY ((merchant_id, day), status, created_at, payment_id): AP3 from lesson 2
    private fun byMerchantDay() =
        WideColumnTable(PrimaryKey(listOf("merchant_id", "day"), listOf("status", "created_at", "payment_id")))

    private fun pay(account: String, at: String, id: String, status: String = "SETTLED", amount: String = "1000") =
        mapOf("account_id" to account, "created_at" to at, "payment_id" to id, "status" to status, "amount_minor" to amount)

    private fun ids(r: ReadResult) = r.rows.map { it["payment_id"] }

    @Test
    fun `a partition comes back in clustering order whatever order the rows were written in`() {
        val t = byAccount()
        t.insert(pay("A-1001", "10:30", "pay-81730"), timestamp = 1)
        t.insert(pay("A-1001", "08:15", "pay-81701"), timestamp = 2)
        t.flush()
        t.insert(pay("A-1001", "09:40", "pay-81720"), timestamp = 3)
        t.insert(pay("A-2002", "09:55", "pay-81724"), timestamp = 4)
        t.flush()
        t.insert(pay("A-1001", "09:00", "pay-81723"), timestamp = 5) // still in the memtable

        val r = t.select(Select(where = mapOf("account_id" to "A-1001")), now = 10)

        assertThat(ids(r)).containsExactly("pay-81701", "pay-81723", "pay-81720", "pay-81730")
        assertThat(r.partitionsRead).isEqualTo(1)
        assertThat(t.sstableCount).isEqualTo(2)
    }

    @Test
    fun `a range on the first clustering column reads one slice and stops at the limit`() {
        val t = byAccount()
        for (h in 10..23) t.insert(pay("A-1001", "%02d:00".format(h), "pay-$h"), timestamp = h.toLong())
        t.flush()

        val r = t.select(Select(where = mapOf("account_id" to "A-1001"), range = Range("created_at", from = "12:00", until = "18:00"), limit = 3), now = 100)

        assertThat(ids(r)).containsExactly("pay-12", "pay-13", "pay-14")
        // the store seeks to 12:00 and stops after three rows: it never touches the other eleven
        assertThat(r.liveRowsRead).isEqualTo(3)
    }

    @Test
    fun `equality on a clustering prefix, then a range on the next column, is one slice`() {
        val t = byMerchantDay()
        fun mp(status: String, at: String, id: String) =
            mapOf("merchant_id" to "M-0042", "day" to "2026-11-07", "status" to status, "created_at" to at, "payment_id" to id)
        t.insert(mp("SETTLED", "08:15", "pay-81701"), 1)
        t.insert(mp("FAILED", "09:40", "pay-81720"), 2)
        t.insert(mp("FAILED", "09:55", "pay-81724"), 3)
        t.insert(mp("FAILED", "08:01", "pay-81690"), 4)
        t.insert(mp("SETTLED", "11:05", "pay-81741"), 5)

        val q = Select(where = mapOf("merchant_id" to "M-0042", "day" to "2026-11-07", "status" to "FAILED"), range = Range("created_at", from = "09:00"))
        val r = t.select(q, now = 10)

        assertThat(t.filteringReason(q)).isNull()
        assertThat(ids(r)).containsExactly("pay-81720", "pay-81724")
        assertThat(r.liveRowsRead).isEqualTo(2)
    }

    @Test
    fun `without the whole partition key a query needs ALLOW FILTERING, and then it reads every partition`() {
        val t = byAccount()
        for (a in 1..50) for (n in 1..4) t.insert(pay("A-%04d".format(a), "0$n:00", "pay-$a-$n", status = if (a == 7 && n == 2) "FAILED" else "SETTLED"), 1)
        t.flush()
        val q = Select(where = mapOf("status" to "FAILED"))

        assertThat(t.filteringReason(q)).isEqualTo(WideColumnTable.ALLOW_FILTERING)
        assertThatThrownBy { t.select(q, now = 10) }
            .isInstanceOf(InvalidQueryException::class.java)
            .hasMessageContaining("use ALLOW FILTERING")

        val r = t.select(q.copy(allowFiltering = true), now = 10)
        assertThat(ids(r)).containsExactly("pay-7-2")
        // one answer, 200 rows read: the cost follows the table, not the answer
        assertThat(r.partitionsRead).isEqualTo(50)
        assertThat(r.liveRowsRead).isEqualTo(200)
        // a partition key that's only half there is no better
        val half = byMerchantDay()
        assertThat(half.filteringReason(Select(where = mapOf("merchant_id" to "M-0042")))).isEqualTo(WideColumnTable.ALLOW_FILTERING)
    }

    @Test
    fun `a filter on a regular column needs ALLOW FILTERING and reads the whole partition`() {
        val t = byAccount()
        for (n in 0 until 30) t.insert(pay("A-1001", "%02d:00".format(n % 24) + n, "pay-$n", amount = (n * 100).toString()), 1)
        val q = Select(where = mapOf("account_id" to "A-1001", "status" to "FAILED"))
        assertThat(t.filteringReason(q)).isEqualTo(WideColumnTable.ALLOW_FILTERING)

        val r = t.select(q.copy(allowFiltering = true), now = 10)
        assertThat(r.rows).isEmpty()
        assertThat(r.partitionsRead).isEqualTo(1)
        assertThat(r.liveRowsRead).isEqualTo(30)
    }

    @Test
    fun `skipping a clustering column is refused with Cassandra's message`() {
        val t = byMerchantDay()
        val skipStatus = Select(where = mapOf("merchant_id" to "M-0042", "day" to "2026-11-07"), range = Range("created_at", from = "09:00"))
        assertThat(t.filteringReason(skipStatus))
            .isEqualTo("PRIMARY KEY column \"created_at\" cannot be restricted as preceding column \"status\" is not restricted")
        assertThatThrownBy { t.select(skipStatus, now = 1) }.isInstanceOf(InvalidQueryException::class.java)

        val skipEq = Select(where = mapOf("merchant_id" to "M-0042", "day" to "2026-11-07", "payment_id" to "pay-81720"))
        assertThat(t.filteringReason(skipEq))
            .isEqualTo("PRIMARY KEY column \"payment_id\" cannot be restricted as preceding column \"status\" is not restricted")
    }

    @Test
    fun `the newest timestamp wins across the memtable and SSTables, whatever order they arrive in`() {
        val t = byAccount()
        t.insert(pay("A-1001", "09:00", "pay-81723", status = "AUTHORIZED"), timestamp = 100)
        t.flush()
        t.insert(pay("A-1001", "09:00", "pay-81723", status = "CAPTURED"), timestamp = 200)
        t.flush()
        // a late write with an OLDER timestamp (a slow client, a skewed clock): it loses
        t.insert(pay("A-1001", "09:00", "pay-81723", status = "VOIDED"), timestamp = 150)

        val r = t.select(Select(where = mapOf("account_id" to "A-1001")), now = 300)

        assertThat(r.rows.single()["status"]).isEqualTo("CAPTURED")
        assertThat(t.mergedPartition(listOf("A-1001")).values.single().timestamp).isEqualTo(200)
    }

    @Test
    fun `a delete writes a tombstone that hides older data and that every read steps over`() {
        val t = byAccount()
        t.insert(pay("A-1001", "08:15", "pay-81701"), 1)
        t.insert(pay("A-1001", "09:40", "pay-81720"), 2)
        t.flush()
        t.delete(mapOf("account_id" to "A-1001", "created_at" to "08:15", "payment_id" to "pay-81701"), timestamp = 3)

        val r = t.select(Select(where = mapOf("account_id" to "A-1001")), now = 10)

        assertThat(ids(r)).containsExactly("pay-81720")
        assertThat(r.tombstonesRead).isEqualTo(1)
        // the SSTable still holds the old row: nothing was removed, only shadowed
        assertThat(t.sstables.single().partitions[listOf("A-1001")]).hasSize(2)
        // a delete with an older timestamp than the data doesn't hide it
        t.delete(mapOf("account_id" to "A-1001", "created_at" to "09:40", "payment_id" to "pay-81720"), timestamp = 1)
        assertThat(ids(t.select(Select(where = mapOf("account_id" to "A-1001")), now = 10))).containsExactly("pay-81720")
    }

    @Test
    fun `a row with a TTL disappears at its expiry and then counts as a tombstone`() {
        val t = byAccount()
        t.insert(pay("A-1001", "09:00", "pay-81723"), timestamp = 1_000, ttlSeconds = 60)
        t.insert(pay("A-1001", "09:05", "pay-81725"), timestamp = 1_000)
        val q = Select(where = mapOf("account_id" to "A-1001"))

        assertThat(ids(t.select(q, now = 1_059))).containsExactly("pay-81723", "pay-81725")
        val later = t.select(q, now = 1_060)
        assertThat(ids(later)).containsExactly("pay-81725")
        assertThat(later.tombstonesRead).isEqualTo(1)
    }

    @Test
    fun `a queue partition fills with tombstones until the read fails`() {
        // a payout queue: the worker inserts, processes, deletes. The partition keeps every delete.
        val t = WideColumnTable(PrimaryKey(listOf("merchant_id"), listOf("payout_id")), tombstoneFailureThreshold = 1_000)
        fun payout(n: Int) = mapOf("merchant_id" to "M-0042", "payout_id" to "%06d".format(n), "amount_minor" to "500")
        for (n in 0 until 2_000) t.insert(payout(n), timestamp = n.toLong())
        t.flush()
        for (n in 0 until 990) t.delete(payout(n), timestamp = 10_000L + n)
        t.flush()
        val next10 = Select(where = mapOf("merchant_id" to "M-0042"), limit = 10)

        val r = t.select(next10, now = 20_000)
        assertThat(r.rows.map { it["payout_id"] }.first()).isEqualTo("000990")
        assertThat(r.liveRowsRead).isEqualTo(10)
        assertThat(r.tombstonesRead).isEqualTo(990)

        // twenty more processed payouts: the next read has to step over 1,010 tombstones
        for (n in 990 until 1_010) t.delete(payout(n), timestamp = 20_000L + n)
        assertThatThrownBy { t.select(next10, now = 30_000) }.isInstanceOf(TombstoneOverwhelmingException::class.java)
    }

    @Test
    fun `compaction merges the SSTables into one, keeps the newest versions and keeps young tombstones`() {
        val t = byAccount()
        t.insert(pay("A-1001", "08:15", "pay-81701", status = "AUTHORIZED"), 1)
        t.insert(pay("A-1001", "09:40", "pay-81720"), 1)
        t.flush()
        t.insert(pay("A-1001", "08:15", "pay-81701", status = "SETTLED"), 2)
        t.flush()
        t.delete(mapOf("account_id" to "A-1001", "created_at" to "09:40", "payment_id" to "pay-81720"), timestamp = 3)
        t.flush()
        assertThat(t.sstableCount).isEqualTo(3)

        t.compact(now = 100, gcGraceSeconds = 864_000)

        assertThat(t.sstableCount).isEqualTo(1)
        val rows = t.sstables.single().partitions.getValue(listOf("A-1001"))
        assertThat(rows).hasSize(2) // the settled payment, and the tombstone: it's younger than gc_grace
        assertThat(rows.values.first().values?.get("status")).isEqualTo("SETTLED")
        assertThat(rows.values.last().isTombstone).isTrue()
        val r = t.select(Select(where = mapOf("account_id" to "A-1001")), now = 100)
        assertThat(ids(r)).containsExactly("pay-81701")
        assertThat(r.tombstonesRead).isEqualTo(1)
    }

    @Test
    fun `a tombstone purged before repair lets the deleted row come back`() {
        val gcGrace = 864_000L // 10 days, Cassandra's default gc_grace_seconds
        val a = byAccount()
        val b = byAccount()
        // both replicas get the payment; only A gets the delete, because B was down
        for (r in listOf(a, b)) r.insert(pay("A-1001", "08:15", "pay-81701"), timestamp = 1)
        a.delete(mapOf("account_id" to "A-1001", "created_at" to "08:15", "payment_id" to "pay-81701"), timestamp = 100)
        a.flush()
        b.flush()
        val q = Select(where = mapOf("account_id" to "A-1001"))

        // compaction inside gc_grace keeps the tombstone, so a repair from stale B changes nothing
        a.compact(now = 100 + gcGrace - 1, gcGraceSeconds = gcGrace)
        a.repairFrom(b)
        assertThat(a.select(q, now = 100 + gcGrace).rows).isEmpty()

        // after gc_grace compaction purges it, and the same repair resurrects the row: a zombie
        a.flush()
        a.compact(now = 100 + gcGrace, gcGraceSeconds = gcGrace)
        assertThat(a.select(q, now = 100 + gcGrace).tombstonesRead).isZero()
        a.repairFrom(b)
        assertThat(ids(a.select(q, now = 100 + gcGrace))).containsExactly("pay-81701")
    }
}
