package sfz.nosql.l01

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test
import sfz.nosql.l01.MiniBigtable.CellKey

class MiniBigtableTest {
    // a merchant's payment history, Bigtable style: one row per payment, two column families
    private fun table(maxVersions: Int = 3) = MiniBigtable(setOf("pay", "risk"), maxVersions)

    @Test
    fun `cell keys sort by row, then column, then newest timestamp first`() {
        val keys = listOf(
            CellKey("M-0042#pay-2", "pay:amount", 100),
            CellKey("M-0042#pay-1", "pay:status", 100),
            CellKey("M-0042#pay-1", "pay:status", 300),
            CellKey("M-0042#pay-1", "pay:amount", 100),
            CellKey("M-0042#pay-1", "pay:status", 200),
        )
        assertThat(keys.sorted()).containsExactly(
            CellKey("M-0042#pay-1", "pay:amount", 100),
            CellKey("M-0042#pay-1", "pay:status", 300),
            CellKey("M-0042#pay-1", "pay:status", 200),
            CellKey("M-0042#pay-1", "pay:status", 100),
            CellKey("M-0042#pay-2", "pay:amount", 100),
        )
    }

    @Test
    fun `put rejects a column family the table never declared`() {
        val t = table()
        assertThatThrownBy { t.put("M-0042#pay-1", "fraud:score", 100, "0.93") }
            .isInstanceOf(IllegalArgumentException::class.java)
        assertThatThrownBy { t.put("M-0042#pay-1", "status", 100, "SETTLED") } // no family at all
            .isInstanceOf(IllegalArgumentException::class.java)
        assertThat(t.cellCount()).isZero()
    }

    @Test
    fun `get returns the newest version by timestamp, not the last one written`() {
        val t = table()
        t.put("M-0042#pay-1", "pay:status", 200, "SETTLED")
        t.put("M-0042#pay-1", "pay:status", 100, "AUTHORIZED") // a late, older write arrives second
        assertThat(t.get("M-0042#pay-1", "pay:status")).isEqualTo("SETTLED")
        assertThat(t.get("M-0042#pay-1", "pay:amount")).isNull()
        assertThat(t.get("M-0042#pay-9", "pay:status")).isNull()
    }

    @Test
    fun `versions come newest first and only maxVersions are kept`() {
        val t = table(maxVersions = 3)
        for ((ts, status) in listOf(100L to "CREATED", 400L to "SETTLED", 200L to "AUTHORIZED", 300L to "CAPTURED", 500L to "REFUNDED")) {
            t.put("M-0042#pay-1", "pay:status", ts, status)
        }
        t.put("M-0042#pay-1", "risk:score", 150, "0.12")

        assertThat(t.versions("M-0042#pay-1", "pay:status").map { it.timestamp }).containsExactly(500L, 400L, 300L)
        assertThat(t.versions("M-0042#pay-1", "pay:status").first())
            .isEqualTo(Cell("M-0042#pay-1", "pay:status", 500, "REFUNDED"))
        // the cap applies per cell: the risk column keeps its one version
        assertThat(t.cellCount()).isEqualTo(4)
    }

    @Test
    fun `writing the same timestamp again replaces that version`() {
        val t = table()
        t.put("M-0042#pay-1", "pay:amount", 100, "4250")
        t.put("M-0042#pay-1", "pay:amount", 100, "4251")
        assertThat(t.versions("M-0042#pay-1", "pay:amount").map { it.value }).containsExactly("4251")
    }

    @Test
    fun `readRow returns only the columns that row has, newest values, nothing from a neighbouring row`() {
        val t = table()
        t.put("pay-1", "pay:amount", 100, "4250")
        t.put("pay-1", "pay:status", 100, "AUTHORIZED")
        t.put("pay-1", "pay:status", 200, "SETTLED")
        t.put("pay-10", "pay:amount", 100, "999")         // "pay-10" sorts right after "pay-1"
        t.put("pay-10", "risk:score", 100, "0.97")
        t.put("pay-2", "pay:amount", 100, "1999")

        assertThat(t.readRow("pay-1")).containsExactlyEntriesOf(mapOf("pay:amount" to "4250", "pay:status" to "SETTLED"))
        assertThat(t.readRow("pay-10")).containsOnlyKeys("pay:amount", "risk:score")
        assertThat(t.readRow("pay-3")).isEmpty()
    }

    @Test
    fun `scan returns the rows with a prefix in key order and stops at the limit`() {
        val t = table()
        // two merchants, written interleaved and out of order
        t.put("M-0043#2026-11-07T09:00#pay-7", "pay:amount", 1, "700")
        t.put("M-0042#2026-11-07T10:30#pay-3", "pay:amount", 1, "300")
        t.put("M-0042#2026-11-07T08:15#pay-1", "pay:amount", 1, "100")
        t.put("M-0042#2026-11-07T08:15#pay-1", "pay:status", 2, "SETTLED")
        t.put("M-0041#2026-11-07T11:00#pay-0", "pay:amount", 1, "50")
        t.put("M-0042#2026-11-07T09:40#pay-2", "pay:amount", 1, "200")
        t.put("M-0042#2026-11-07T09:40#pay-2", "pay:amount", 5, "201")

        val all = t.scan("M-0042#", 10)
        assertThat(all.map { it.key }).containsExactly(
            "M-0042#2026-11-07T08:15#pay-1",
            "M-0042#2026-11-07T09:40#pay-2",
            "M-0042#2026-11-07T10:30#pay-3",
        )
        assertThat(all[0].columns).containsExactlyEntriesOf(mapOf("pay:amount" to "100", "pay:status" to "SETTLED"))
        assertThat(all[1].columns).containsExactlyEntriesOf(mapOf("pay:amount" to "201"))

        assertThat(t.scan("M-0042#", 2).map { it.key })
            .containsExactly("M-0042#2026-11-07T08:15#pay-1", "M-0042#2026-11-07T09:40#pay-2")
        assertThat(t.scan("M-0042#2026-11-07T09", 10).map { it.key }).containsExactly("M-0042#2026-11-07T09:40#pay-2")
        assertThat(t.scan("M-9999#", 10)).isEmpty()
    }
}
