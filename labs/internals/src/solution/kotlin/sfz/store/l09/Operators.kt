package sfz.store.l09

// Lesson 9 lab: a Volcano-style executor.
// Your job: write next() of Filter, Project and Limit; open() and next() of NestedLoopJoin and HashJoin;
// and BatchFilter.nextBatch() in Vectors.kt. Operator, Scan, Unary, the close() methods, drain(),
// Batch and BatchScan are done. The tests wrap operators in a Counting operator to see what each one pulls.

/** A row: column values by position. A value may be null, as in SQL. */
typealias Row = List<Any?>

/**
 * The iterator interface of the Volcano model, the one PostgreSQL's executor uses.
 *
 * A plan is a tree of operators. The caller calls [open] once, then [next] until it returns null, then
 * [close]. Each [next] returns ONE row, and an operator gets its input by calling [next] on its children:
 * rows are pulled up the tree one at a time, only when someone above asks for them.
 */
interface Operator {
    fun open()
    fun next(): Row?
    fun close()
}

/** Produces the rows of a list, in order: the leaf of every plan, like a sequential scan of a table. */
class Scan(private val rows: List<Row>) : Operator {
    private var pos = -1                       // -1: not open
    override fun open() { pos = 0 }
    override fun next(): Row? {
        check(pos >= 0) { "next() before open()" }
        return if (pos < rows.size) rows[pos++] else null
    }
    override fun close() { pos = -1 }
}

/** An operator with one input. It opens and closes its child with itself. */
abstract class Unary(protected val child: Operator) : Operator {
    override fun open() = child.open()
    override fun close() = child.close()
}

/** `WHERE`: passes on only the rows for which [predicate] is true. */
class Filter(child: Operator, private val predicate: (Row) -> Boolean) : Unary(child) {
    override fun next(): Row? {
        while (true) {
            val row = child.next() ?: return null  // the child ran out
            if (predicate(row)) return row         // otherwise skip it and pull the next one
        }
    }
}

/** The `SELECT` list: keeps the [columns] (by position, in this order) of every row. */
class Project(child: Operator, private val columns: List<Int>) : Unary(child) {
    override fun next(): Row? {
        val row = child.next() ?: return null
        return columns.map { row[it] }
    }
}

/** `LIMIT n`: passes on the first [n] rows, and never asks its child for more than [n]. */
class Limit(child: Operator, private val n: Int) : Unary(child) {
    private var produced = 0
    override fun open() { produced = 0; super.open() }
    override fun next(): Row? {
        if (produced >= n) return null             // done: don't pull another row from below
        val row = child.next() ?: return null
        produced++
        return row
    }
}

/**
 * An equi-join, `left.key = right.key`, by nested loops: for every row of [left], scan all of [right] again
 * (close and reopen it) and emit `leftRow + rightRow` for every pair whose keys are equal. A null key never
 * matches anything, as in SQL. [comparisons] counts the pairs examined: |left| x |right|.
 */
class NestedLoopJoin(
    private val left: Operator,
    private val right: Operator,
    private val leftKey: Int,
    private val rightKey: Int,
) : Operator {
    var comparisons = 0L
        private set
    private var outer: Row? = null

    override fun open() {
        left.open()
        outer = left.next()
        if (outer != null) right.open()            // an empty left side never touches the right one
    }

    override fun next(): Row? {
        while (true) {
            val l = outer ?: return null           // the left side ran out: done
            val r = right.next()
            if (r == null) {                       // the inner side is used up for this outer row:
                outer = left.next() ?: return null // take the next outer row, if there is one,
                right.close()                      // and rescan the inner side from the start
                right.open()
                continue
            }
            comparisons++
            val k = l[leftKey]
            if (k != null && k == r[rightKey]) return l + r
        }
    }

    override fun close() {
        left.close()
        right.close()
        outer = null
    }
}

/**
 * An equi-join, `build.key = probe.key`, with a hash table. [open] reads ALL of [build] into a hash table
 * from key to rows (the build phase). Then each [next] pulls rows from [probe] and looks their key up (the
 * probe phase), emitting `buildRow + probeRow` for each match, the same column order as
 * `NestedLoopJoin(build, probe)`. Each input is read once. Rows with a null key are never put in the table
 * and never looked up.
 */
class HashJoin(
    private val build: Operator,
    private val probe: Operator,
    private val buildKey: Int,
    private val probeKey: Int,
) : Operator {
    private val table = HashMap<Any, MutableList<Row>>()
    private var probeRow: Row? = null
    private var matches: Iterator<Row> = emptyList<Row>().iterator()

    override fun open() {
        build.open()
        while (true) {                             // build phase: drain the build side once
            val row = build.next() ?: break
            val k = row[buildKey] ?: continue      // a null key can never match
            table.getOrPut(k) { mutableListOf() } += row
        }
        probe.open()
    }

    override fun next(): Row? {
        while (true) {
            if (matches.hasNext()) return matches.next() + probeRow!!
            val p = probe.next() ?: return null    // probe phase: one lookup per probe row
            probeRow = p
            matches = p[probeKey]?.let { table[it] }?.iterator() ?: emptyList<Row>().iterator()
        }
    }

    override fun close() {
        build.close()
        probe.close()
        table.clear()
        matches = emptyList<Row>().iterator()
    }
}

/** Runs a plan to the end and returns every row it produced. */
fun Operator.drain(): List<Row> {
    open()
    try {
        val out = ArrayList<Row>()
        while (true) out += next() ?: return out
    } finally {
        close()
    }
}
