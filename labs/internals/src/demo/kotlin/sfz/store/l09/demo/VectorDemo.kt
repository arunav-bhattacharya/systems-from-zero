package sfz.store.l09.demo

import java.lang.management.ManagementFactory

/**
 * Runs `SELECT sum(amount_cents) FROM payments WHERE amount_cents > 9000` over 10 million in-memory payments
 * (or as many millions as the first argument says) three ways and prints the CPU time per row:
 *
 * 1. Volcano: Scan -> Filter -> Sum, one `next()` call per row per operator, and the WHERE clause
 *    evaluated by walking a small expression tree for every row, as an interpreter does.
 * 2. Vectorized: the same three operators, but `nextBatch()` hands over 1,024 values at a time and the
 *    filter is one tight loop over a `LongArray`.
 * 3. A hand-written loop: what a query compiler aims to produce.
 *
 * A real engine runs many different plans in one process, so its `next()` call sites see many operator
 * classes and the JIT can't inline them. The demo warms up with several plan shapes and expressions to get
 * the same effect, then prints the best of 5 runs of each plan, in CPU time of the main thread.
 */
fun main(args: Array<String>) {
    val n = (args.firstOrNull()?.toInt() ?: 10) * 1_000_000
    val amounts = LongArray(n) { (it * 7919L) % 10_000 }
    val where: Expr = Gt(Col(0), Const(9_000))
    val expected = amounts.filter { it > 9_000 }.sum()

    fun volcano(): Long = Sum(Filter(Scan(amounts), where)).run()
    fun vectorized(): Long = BatchSum(BatchFilter(BatchScan(amounts), 9_000)).run()
    fun loop(): Long { var s = 0L; for (a in amounts) if (a > 9_000) s += a; return s }

    // Warm-up on a small table. A real server runs many different plans, so each next() and eval()
    // call site sees several classes and the JIT can't inline them away. Run several plan shapes and
    // expressions round-robin BEFORE the JIT compiles anything, so the profiles look like a server's.
    val small = LongArray(20_000) { (it * 7919L) % 10_000 }
    val exprs = listOf(Gt(Col(0), Const(9_000)), Gt(Const(9_000), Col(0)), Gt(Add(Col(0), Const(1)), Const(9_001)))
    repeat(300) { round ->
        val e = exprs[round % exprs.size]
        Sum(Project(Scan(small))).run()
        Sum(Limit(Scan(small), 15_000)).run()
        Sum(Filter(Project(Scan(small)), e)).run()
        Sum(Filter(Limit(Scan(small), 15_000), e)).run()
        Sum(Filter(Scan(small), e)).run()
        BatchSum(BatchFilter(BatchScan(small), 9_000)).run()
    }
    volcano(); vectorized(); loop()
    val cpu = ManagementFactory.getThreadMXBean()
    println("rows: %,d   matching sum: %,d".format(n, expected))
    println("%-12s %10s %10s".format("plan", "cpu ms", "ns/row"))
    for ((name, run) in listOf("volcano" to ::volcano, "vectorized" to ::vectorized, "plain loop" to ::loop)) {
        val best = (1..5).minOf {
            val t0 = cpu.currentThreadCpuTime                  // CPU time, so a busy machine doesn't inflate it
            check(run() == expected) { "$name computed a wrong sum" }
            cpu.currentThreadCpuTime - t0
        }
        println("%-12s %10.1f %10.2f".format(name, best / 1e6, best.toDouble() / n))
    }
}

// ---------------------------------------------------------------- row at a time

/** A row with one column; the scan reuses one instance, as PostgreSQL reuses a tuple slot. */
class Row(var amount: Long)

interface Operator { fun next(): Row? }

class Scan(private val amounts: LongArray) : Operator {
    private var i = 0
    private val row = Row(0)
    override fun next(): Row? {
        if (i == amounts.size) return null
        row.amount = amounts[i++]
        return row
    }
}

class Filter(private val child: Operator, private val predicate: Expr) : Operator {
    override fun next(): Row? {
        while (true) {
            val r = child.next() ?: return null
            if (predicate.eval(r) != 0L) return r
        }
    }
}

class Project(private val child: Operator) : Operator {
    private val out = Row(0)
    override fun next(): Row? = child.next()?.let { out.amount = it.amount; out }
}

class Limit(private val child: Operator, private val n: Int) : Operator {
    private var left = n
    override fun next(): Row? = if (left-- > 0) child.next() else null
}

class Sum(private val child: Operator) {
    fun run(): Long {
        var s = 0L
        while (true) s += (child.next() ?: return s).amount
    }
}

/** The WHERE clause as a tree, evaluated per row: 1 means true, 0 false. */
sealed interface Expr { fun eval(r: Row): Long }
class Col(@Suppress("unused") val index: Int) : Expr { override fun eval(r: Row) = r.amount }
class Const(private val v: Long) : Expr { override fun eval(r: Row) = v }
class Gt(private val a: Expr, private val b: Expr) : Expr {
    override fun eval(r: Row) = if (a.eval(r) > b.eval(r)) 1L else 0L
}
class Add(private val a: Expr, private val b: Expr) : Expr {
    override fun eval(r: Row) = a.eval(r) + b.eval(r)
}

// ---------------------------------------------------------------- a batch at a time

const val BATCH = 1024

/** A batch: [size] values in [values], plus which of them passed the filters so far. */
class Batch(val values: LongArray, var size: Int, val selected: IntArray, var count: Int)

class BatchScan(private val amounts: LongArray) {
    private var pos = 0
    private val batch = Batch(LongArray(BATCH), 0, IntArray(BATCH), 0)
    fun nextBatch(): Batch? {
        if (pos >= amounts.size) return null
        val len = minOf(BATCH, amounts.size - pos)
        System.arraycopy(amounts, pos, batch.values, 0, len)
        pos += len
        batch.size = len
        for (i in 0 until len) batch.selected[i] = i
        batch.count = len
        return batch
    }
}

class BatchFilter(private val child: BatchScan, private val greaterThan: Long) {
    fun nextBatch(): Batch? {
        val b = child.nextBatch() ?: return null
        var k = 0
        for (j in 0 until b.count) {                 // one loop, no calls: the CPU and JIT love this
            val i = b.selected[j]
            if (b.values[i] > greaterThan) b.selected[k++] = i
        }
        b.count = k
        return b
    }
}

class BatchSum(private val child: BatchFilter) {
    fun run(): Long {
        var s = 0L
        while (true) {
            val b = child.nextBatch() ?: return s
            for (j in 0 until b.count) s += b.values[b.selected[j]]
        }
    }
}
