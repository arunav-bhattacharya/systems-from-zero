package sfz.store.l12

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test
import kotlin.random.Random

class MaterializedViewTest {
    /** Applies [change] to the table first and then to the view, the order an AFTER trigger sees it in. */
    private fun PaymentTable.andView(view: IncrementalView, change: Change) {
        apply(change)
        view.apply(change)
    }

    private fun tableOf(vararg payments: Payment) = PaymentTable().apply { payments.forEach { apply(Inserted(it)) } }

    private val p1 = Payment(1, "M-0042", 1_250)
    private val p2 = Payment(2, "M-0042", 300)
    private val p3 = Payment(3, "M-0042", 8_900)
    private val p4 = Payment(4, "M-0007", 4_000)
    private val p5 = Payment(5, "M-0007", 500)
    private val p6 = Payment(6, "M-0313", 70_000)

    @Test
    fun `a full recompute reads every row and writes one view row per merchant`() {
        val work = Work()
        val view = fullRecompute(tableOf(p1, p2, p3, p4, p5, p6), work)
        assertThat(view).hasSize(3)
        assertThat(view["M-0042"]).isEqualTo(Totals("M-0042", 3, 10_450, 300))
        assertThat(view["M-0007"]).isEqualTo(Totals("M-0007", 2, 4_500, 500))
        assertThat(view["M-0313"]).isEqualTo(Totals("M-0313", 1, 70_000, 70_000))
        assertThat(view.getValue("M-0042").avgCents).isCloseTo(3_483.33, within(0.01))
        assertThat(work.baseRowsRead).`as`("rows read").isEqualTo(6)
        assertThat(work.viewRowsWritten).`as`("view rows written").isEqualTo(3)
        assertThat(fullRecompute(PaymentTable(), Work())).`as`("an empty table").isEmpty()
    }

    @Test
    fun `an insert changes one view row and reads nothing from the table`() {
        val table = tableOf(p1, p2, p4)
        val view = IncrementalView(table)
        table.andView(view, Inserted(p3))
        assertThat(view["M-0042"]).isEqualTo(Totals("M-0042", 3, 10_450, 300))
        table.andView(view, Inserted(Payment(7, "M-0042", 100)))
        assertThat(view["M-0042"]).`as`("a new minimum").isEqualTo(Totals("M-0042", 4, 10_550, 100))
        assertThat(view["M-0007"]).`as`("other merchants are untouched").isEqualTo(Totals("M-0007", 1, 4_000, 4_000))
        assertThat(view.work.baseRowsRead).isZero()
        assertThat(view.work.viewRowsWritten).isEqualTo(2)
    }

    @Test
    fun `a payment for a new merchant adds a view row`() {
        val table = tableOf(p1)
        val view = IncrementalView(table)
        table.andView(view, Inserted(p6))
        assertThat(view.snapshot()).containsOnlyKeys("M-0042", "M-0313")
        assertThat(view["M-0313"]).isEqualTo(Totals("M-0313", 1, 70_000, 70_000))
        assertThat(view.work.rowsTouched).isEqualTo(1)
    }

    @Test
    fun `deleting a payment that isn't the minimum only subtracts it`() {
        val table = tableOf(p1, p2, p3)
        val view = IncrementalView(table)
        table.andView(view, Deleted(p3))
        assertThat(view["M-0042"]).isEqualTo(Totals("M-0042", 2, 1_550, 300))
        assertThat(view["M-0042"]!!.avgCents).isEqualTo(775.0)
        assertThat(view.work.baseRowsRead).`as`("COUNT and SUM never need the table").isZero()
        assertThat(view.minRescans).isZero()
    }

    @Test
    fun `deleting a merchant's last payment removes its row`() {
        val table = tableOf(p1, p6)
        val view = IncrementalView(table)
        table.andView(view, Deleted(p6))
        assertThat(view["M-0313"]).isNull()
        assertThat(view.snapshot()).containsOnlyKeys("M-0042")
        assertThat(view.work.viewRowsWritten).isEqualTo(1)
        assertThat(view.work.baseRowsRead).isZero()
    }

    @Test
    fun `deleting the minimum rescans that merchant's rows and no others`() {
        val table = tableOf(p1, p2, p3, p4, p5, p6)
        val view = IncrementalView(table)
        table.andView(view, Deleted(p2))                     // 300 was M-0042's minimum
        assertThat(view["M-0042"]).isEqualTo(Totals("M-0042", 2, 10_150, 1_250))
        assertThat(view.minRescans).isEqualTo(1)
        assertThat(view.work.baseRowsRead).`as`("M-0042's two remaining rows").isEqualTo(2)
        assertThat(view.work.viewRowsWritten).isEqualTo(1)
    }

    @Test
    fun `deleting one of two equal minimums still rescans, because the view can't tell them apart`() {
        val table = tableOf(p1, p2, Payment(8, "M-0042", 300))
        val view = IncrementalView(table)
        table.andView(view, Deleted(p2))
        assertThat(view["M-0042"]).isEqualTo(Totals("M-0042", 2, 1_550, 300))
        assertThat(view.minRescans).isEqualTo(1)
    }

    @Test
    fun `the incremental view always equals a full recompute`() {
        val rnd = Random(12)
        val table = PaymentTable()
        val live = ArrayList<Payment>()
        var nextId = 1L
        fun newPayment() = Payment(nextId++, "M-%04d".format(rnd.nextInt(30)), 1L + rnd.nextInt(20_000))
        repeat(2_000) { val p = newPayment(); table.apply(Inserted(p)); live += p }
        val view = IncrementalView(table)
        assertThat(view.snapshot()).isEqualTo(fullRecompute(table, Work()))
        for (step in 1..3_000) {
            val change = if (live.isEmpty() || rnd.nextInt(100) < 45) Inserted(newPayment().also { live += it })
            else Deleted(live.removeAt(rnd.nextInt(live.size)))
            table.andView(view, change)
            if (step % 100 == 0) assertThat(view.snapshot()).`as`("after $step changes").isEqualTo(fullRecompute(table, Work()))
        }
        assertThat(view.minRescans).`as`("some deletes hit a minimum").isPositive()
    }

    @Test
    fun `incremental maintenance touches a tiny fraction of what recomputing after every change does`() {
        val rnd = Random(7)
        val table = PaymentTable()
        val live = ArrayList<Payment>()
        var nextId = 1L
        fun newPayment() = Payment(nextId++, "M-%04d".format(rnd.nextInt(100)), 1L + rnd.nextInt(100_000))
        repeat(10_000) { val p = newPayment(); table.apply(Inserted(p)); live += p }
        val view = IncrementalView(table)
        val recompute = Work()
        repeat(500) { i ->
            val change = if (i % 2 == 0) Inserted(newPayment().also { live += it }) else Deleted(live.removeAt(rnd.nextInt(live.size)))
            table.andView(view, change)
            fullRecompute(table, recompute)                    // what REFRESH after every change would cost
        }
        assertThat(recompute.baseRowsRead).`as`("10,001 rows after each insert, 10,000 after each delete")
            .isEqualTo(250L * 10_001 + 250L * 10_000)
        assertThat(view.work.viewRowsWritten).`as`("one view row per change").isEqualTo(500)
        assertThat(view.work.rowsTouched * 1_000).`as`("under 0.1% of the recompute's rows")
            .isLessThan(recompute.rowsTouched)
    }

    @Test
    fun `a MinTracker keeps the minimum through deletes and duplicates`() {
        val m = MinTracker()
        assertThat(m.min).isNull()
        listOf(1_250L, 300, 8_900, 300).forEach(m::add)
        assertThat(m.min).isEqualTo(300)
        assertThat(m.size).isEqualTo(4)
        m.remove(300)
        assertThat(m.min).`as`("the second 300 is still there").isEqualTo(300)
        m.remove(300)
        assertThat(m.min).isEqualTo(1_250)
        m.remove(1_250)
        m.remove(8_900)
        assertThat(m.min).isNull()
        assertThat(m.size).isZero()
        assertThatThrownBy { m.remove(42) }.isInstanceOf(IllegalArgumentException::class.java)
    }
}
