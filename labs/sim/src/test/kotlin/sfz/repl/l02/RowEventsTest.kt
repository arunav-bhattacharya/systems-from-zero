package sfz.repl.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/** Exercise 1, [rowEvents]: what a statement did to each row. */
class RowEventsTest {
    private fun row(id: Long, fee: Long = 0) = Row(id, "m1", 1_000, fee, "ref$id", 1_000_000)

    @Test
    fun `a new row is an insert with every column`() {
        val events = rowEvents(mapOf(1L to row(1)), mapOf(1L to row(1), 2L to row(2)))
        assertThat(events).containsExactly(RowEvent.Inserted(row(2)))
    }

    @Test
    fun `a changed row is an update with the new values, and a removed row is a delete with only the key`() {
        val before = mapOf(1L to row(1), 2L to row(2), 3L to row(3))
        val after = mapOf(1L to row(1, fee = 30), 3L to row(3))
        assertThat(rowEvents(before, after)).containsExactly(RowEvent.Updated(row(1, fee = 30)), RowEvent.Deleted(2))
    }

    @Test
    fun `untouched rows produce nothing, and events come in id order`() {
        val before = mapOf(5L to row(5), 9L to row(9), 2L to row(2))
        val after = mapOf(9L to row(9, fee = 1), 2L to row(2), 7L to row(7))
        assertThat(rowEvents(before, after)).containsExactly(
            RowEvent.Deleted(5), RowEvent.Inserted(row(7)), RowEvent.Updated(row(9, fee = 1)),
        )
    }

    @Test
    fun `one UPDATE statement that touches three rows is three row events`() {
        val p = TwoServers()
        p.sixPayments()
        p.run(Statement.AddFee("m1", 30))
        assertThat(p.leader.statementLog.last().sql).isEqualTo("UPDATE payments SET fee = fee + 30 WHERE merchant = 'm1'")
        val last = p.leader.rowLog.takeLast(3)
        assertThat(last).allMatch { it is RowEvent.Updated && (it as RowEvent.Updated).row.feeCents == 30L }
        assertThat(last.map { it.id }).containsExactly(1L, 3L, 5L)
        assertThat(p.leader.rowLog).hasSize(9)                    // 6 inserts + 3 updates, from 7 statements
    }
}
