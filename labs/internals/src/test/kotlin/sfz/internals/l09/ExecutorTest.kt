package sfz.internals.l09

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.random.Random

/** Wraps an operator and counts what its parent asks of it. */
class Counting(private val child: Operator) : Operator {
    var opens = 0; private set
    var nexts = 0; private set
    var rows = 0; private set
    var closes = 0; private set
    override fun open() { opens++; child.open() }
    override fun next(): Row? { nexts++; return child.next()?.also { rows++ } }
    override fun close() { closes++; child.close() }
}

/** The same, for batches. */
class CountingBatches(private val child: BatchOperator) : BatchOperator {
    var calls = 0; private set
    override fun open() = child.open()
    override fun nextBatch(): Batch? { calls++; return child.nextBatch() }
    override fun close() = child.close()
}

class ExecutorTest {
    // payments: (id, merchant_id, amount_cents); merchants: (id, name)
    private val payments: List<Row> = (1L..1_000L).map { listOf(it, it % 20, (it * 7919) % 10_000) }
    private val merchants: List<Row> = (0L..19L).map { listOf(it, "merchant-$it") }

    @Test
    fun `scan, filter and project give what a collection pipeline gives`() {
        val plan = Project(Filter(Scan(payments)) { (it[2] as Long) > 9_000 }, listOf(0, 2))
        val expected = payments.filter { (it[2] as Long) > 9_000 }.map { listOf(it[0], it[2]) }
        assertThat(plan.drain()).isEqualTo(expected)
    }

    @Test
    fun `next returns one row per call and null at the end`() {
        val plan = Filter(Scan(payments.take(5))) { (it[0] as Long) % 2 == 1L }
        plan.open()
        assertThat(plan.next()).isEqualTo(payments[0])
        assertThat(plan.next()).isEqualTo(payments[2])
        assertThat(plan.next()).isEqualTo(payments[4])
        assertThat(plan.next()).isNull()
        plan.close()
    }

    @Test
    fun `limit pulls only the rows it needs`() {
        val scan = Counting(Scan(payments))
        val plan = Limit(Filter(scan) { (it[0] as Long) % 10 == 0L }, 3)
        assertThat(plan.drain().map { it[0] }).containsExactly(10L, 20L, 30L)
        assertThat(scan.rows).`as`("rows the scan produced for LIMIT 3").isEqualTo(30)
        val all = Counting(Scan(payments))
        assertThat(Limit(all, 2_000).drain()).hasSize(1_000)
        assertThat(all.nexts).`as`("next() calls on a scan of 1,000 rows under a bigger limit").isEqualTo(1_001)
    }

    @Test
    fun `close reaches every operator in the tree`() {
        val p = Counting(Scan(payments))
        val m = Counting(Scan(merchants))
        val m2 = Counting(Scan(merchants))
        val plan = Limit(Project(HashJoin(m, NestedLoopJoin(Filter(p) { true }, m2, 1, 0), 0, 1), listOf(0)), 5)
        assertThat(plan.drain()).hasSize(5)
        for ((name, c) in listOf("payments" to p, "merchants (build)" to m, "merchants (inner)" to m2)) {
            assertThat(c.closes).`as`("closes of $name").isGreaterThanOrEqualTo(1)
            assertThat(c.opens).`as`("opens of $name").isGreaterThanOrEqualTo(1)
        }
    }

    @Test
    fun `a nested loop join rescans its inner input once per outer row`() {
        val outer = Counting(Scan(payments.take(100)))
        val inner = Counting(Scan(merchants))
        val join = NestedLoopJoin(outer, inner, leftKey = 1, rightKey = 0)
        val rows = join.drain()
        assertThat(rows).hasSize(100)
        assertThat(rows.first()).isEqualTo(listOf(1L, 1L, 7919L, 1L, "merchant-1"))
        assertThat(inner.opens).`as`("inner scans").isEqualTo(100)
        assertThat(inner.rows).`as`("inner rows pulled: 100 x 20").isEqualTo(2_000)
        assertThat(join.comparisons).isEqualTo(2_000)
        assertThat(outer.rows).isEqualTo(100)
    }

    @Test
    fun `a nested loop join with an empty outer side never reads the inner side`() {
        val inner = Counting(Scan(merchants))
        assertThat(NestedLoopJoin(Scan(emptyList()), inner, 0, 0).drain()).isEmpty()
        assertThat(inner.nexts).isZero()
    }

    @Test
    fun `a hash join reads each input once`() {
        val build = Counting(Scan(merchants))
        val probe = Counting(Scan(payments))
        val rows = HashJoin(build, probe, buildKey = 0, probeKey = 1).drain()
        assertThat(rows).hasSize(1_000)
        assertThat(rows).contains(listOf(1L, "merchant-1", 1L, 1L, 7919L))
        assertThat(build.rows).`as`("build rows pulled").isEqualTo(20)
        assertThat(build.opens).isEqualTo(1)
        assertThat(probe.rows).`as`("probe rows pulled").isEqualTo(1_000)
        assertThat(probe.opens).isEqualTo(1)
    }

    @Test
    fun `the build phase runs in open, before the first probe row is read`() {
        val build = Counting(Scan(merchants))
        val probe = Counting(Scan(payments))
        val join = HashJoin(build, probe, 0, 1)
        join.open()
        assertThat(build.rows).`as`("build rows after open()").isEqualTo(20)
        assertThat(probe.rows).`as`("probe rows after open()").isZero()
        join.next()
        assertThat(probe.rows).`as`("probe rows after the first next()").isEqualTo(1)
        join.close()
    }

    @Test
    fun `hash join and nested loop join agree on random data with duplicates and nulls`() {
        val rnd = Random(42)
        fun key(): Long? = if (rnd.nextInt(10) == 0) null else rnd.nextLong(15)
        repeat(20) { round ->
            val left = List(rnd.nextInt(0, 60)) { i -> listOf(key(), "L$round-$i") }
            val right = List(rnd.nextInt(0, 60)) { i -> listOf("R$round-$i", key()) }
            val nlj = NestedLoopJoin(Scan(left), Scan(right), 0, 1).drain()
            val hj = HashJoin(Scan(left), Scan(right), 0, 1).drain()
            assertThat(hj).`as`("round $round").containsExactlyInAnyOrderElementsOf(nlj)
            assertThat(nlj.none { it[0] == null }).`as`("null keys never match").isTrue()
        }
    }

    @Test
    fun `a vectorized filter returns the same rows in batches`() {
        val n = 10_000
        val ids = LongArray(n) { it.toLong() }
        val amounts = LongArray(n) { (it * 7919L) % 10_000 }
        val scan = CountingBatches(BatchScan(listOf(ids, amounts)))
        val filter = BatchFilter(scan, column = 1, greaterThan = 9_000)
        val got = ArrayList<Row>()
        filter.open()
        while (true) {
            val b = filter.nextBatch() ?: break
            assertThat(b.size).`as`("a batch is never empty").isPositive()
            for (i in 0 until b.size) got += b.row(i)
        }
        filter.close()
        val rows = (0 until n).map { listOf(ids[it], amounts[it]) }
        assertThat(got).isEqualTo(Filter(Scan(rows)) { (it[1] as Long) > 9_000 }.drain())
        assertThat(scan.calls).`as`("batches pulled for 10,000 rows: 9 full, 1 partial, then null").isEqualTo(11)
    }

    @Test
    fun `a vectorized filter skips batches where nothing passes`() {
        val values = LongArray(3 * BATCH_SIZE) { if (it == 2 * BATCH_SIZE + 5) 99 else 1 }
        val filter = BatchFilter(BatchScan(listOf(values)), 0, 50)
        filter.open()
        val b = filter.nextBatch()
        assertThat(b?.size).isEqualTo(1)
        assertThat(b?.row(0)).isEqualTo(listOf(99L))
        assertThat(filter.nextBatch()).isNull()
        filter.close()
    }
}
