package sfz.store.l10

// Lesson 10 lab, part 2: estimate join sizes and choose a join order by dynamic programming.
// Your job: joinSelectivity(), JoinGraph.estimate() and bestPlan(). Sets of tables are bitmasks:
// bit t is set when table t is in the set, so {0, 2} is 0b101 = 5. JoinGraph.connects(), the Plan
// classes, costWith() and describe() are done.

/**
 * Selectivity of the join condition `R.x = S.y`: `1 / max(distinct x, distinct y)`, the formula PostgreSQL
 * uses when it knows nothing else. It assumes every value of the column with fewer distinct values finds
 * a partner in the other column. For a foreign key into a primary key it gives exactly the child's rows.
 */
fun joinSelectivity(distinctLeft: Long, distinctRight: Long): Double =
    1.0 / maxOf(distinctLeft, distinctRight)

/** A table in the FROM list, with the rows the planner expects from it after its own WHERE conditions. */
data class Table(val name: String, val rows: Double)

/** A join predicate between tables [a] and [b] (positions in the table list) that keeps [selectivity] of the pairs. */
data class Edge(val a: Int, val b: Int, val selectivity: Double)

/** The tables of one query and the join predicates between them. */
class JoinGraph(val tables: List<Table>, val edges: List<Edge>) {
    init {
        require(tables.size in 1..20) { "1 to 20 tables" }
        for (e in edges) require(e.a in tables.indices && e.b in tables.indices && e.a != e.b) { "bad edge $e" }
    }

    val size: Int get() = tables.size

    /** The set of all tables. */
    val all: Int get() = (1 shl size) - 1

    /** True if some predicate joins a table in [left] to a table in [right] (both bitmasks). */
    fun connects(left: Int, right: Int): Boolean = edges.any { e ->
        (left.has(e.a) && right.has(e.b)) || (left.has(e.b) && right.has(e.a))
    }

    /**
     * The estimated rows of joining every table in [set]: the product of the tables' rows, times the
     * selectivity of every predicate whose two tables are both in [set]. Multiplying is the independence
     * assumption again, now across tables. For a single table it is that table's rows.
     */
    fun estimate(set: Int): Double {
        var rows = 1.0
        for (t in tables.indices) if (set.has(t)) rows *= tables[t].rows        // every pair of rows...
        for (e in edges) if (set.has(e.a) && set.has(e.b)) rows *= e.selectivity // ...that every predicate keeps
        return rows
    }
}

/** True if table [t] is in this bitmask set. */
fun Int.has(t: Int): Boolean = (this shr t) and 1 == 1

/**
 * A join tree. [rows] is its output size and [cost] the lab's cost model: the total number of rows that
 * all the joins in the tree produce. Scanning a table costs 0 here; what differs between join orders is the
 * size of the intermediate results. (Leis et al. found such a simple model about as good as PostgreSQL's
 * detailed one; the estimates matter far more.)
 */
sealed interface Plan {
    val set: Int
    val rows: Double
    val cost: Double
}

/** A table on its own. */
class Leaf(val table: Int, override val rows: Double) : Plan {
    override val set: Int = 1 shl table
    override val cost: Double = 0.0
}

/** Joins two plans over disjoint sets of tables. Its cost: both inputs' costs plus its own output rows. */
class Join(val left: Plan, val right: Plan, override val rows: Double) : Plan {
    init {
        require(left.set and right.set == 0) { "the two sides of a join must not share tables" }
    }

    override val set: Int = left.set or right.set
    override val cost: Double = left.cost + right.cost + rows
}

/**
 * The cheapest join tree over all the tables of [graph], found by dynamic programming over sets of tables,
 * the method of System R (Selinger et al., 1979) that PostgreSQL still uses for up to 12 tables.
 *
 * [rows] gives the output rows of joining a set of tables: the estimates by default, or real counts.
 *
 * The idea: the best plan for a set S is the best way to split S into two smaller sets L and R (each with
 * its own best plan, already computed) and join them. So:
 * 1. best[{t}] = Leaf(t, rows({t})) for every table t.
 * 2. For every set S with two or more tables, from small sets to big ones (counting S upward from 1
 *    visits every subset of S before S), try every split into a non-empty L and R = S - L. Skip it if
 *    either side has no plan or no predicate connects L and R (that would be a cross product).
 *    Candidate: Join(best[L], best[R], rows(S)). Keep the cheapest in best[S].
 * 3. Return best[all tables]. Throw [IllegalArgumentException] if there is none (the graph isn't connected).
 */
fun bestPlan(graph: JoinGraph, rows: (Int) -> Double = graph::estimate): Plan {
    val best = arrayOfNulls<Plan>(graph.all + 1)
    for (t in 0 until graph.size) best[1 shl t] = Leaf(t, rows(1 shl t))
    for (set in 1..graph.all) {                        // numeric order: every subset of set comes earlier
        if (Integer.bitCount(set) < 2) continue
        val out = rows(set)                            // the same for every way of building this set
        var left = (set - 1) and set                   // walk the non-empty proper subsets of set
        while (left > 0) {
            val right = set xor left
            val l = best[left]
            val r = best[right]
            if (l != null && r != null && graph.connects(left, right)) {
                val candidate = Join(l, r, out)
                val current = best[set]
                if (current == null || candidate.cost < current.cost) best[set] = candidate
            }
            left = (left - 1) and set
        }
    }
    return best[graph.all] ?: throw IllegalArgumentException("no plan without a cross product: the join graph is not connected")
}

/** The cost the same tree has when the real output sizes are [rows]: what it actually does at run time. */
fun Plan.costWith(rows: (Int) -> Double): Double = when (this) {
    is Leaf -> 0.0
    is Join -> left.costWith(rows) + right.costWith(rows) + rows(set)
}

/**
 * The tree as text, the side with more tables first (on a tie, the side with the lower table number):
 * `((merchants JOIN payments) JOIN chargebacks)`.
 */
fun Plan.describe(graph: JoinGraph): String = when (this) {
    is Leaf -> graph.tables[table].name
    is Join -> {
        val nl = Integer.bitCount(left.set)
        val nr = Integer.bitCount(right.set)
        val leftFirst = nl > nr || (nl == nr && Integer.numberOfTrailingZeros(left.set) < Integer.numberOfTrailingZeros(right.set))
        val (a, b) = if (leftFirst) left to right else right to left
        "(${a.describe(graph)} JOIN ${b.describe(graph)})"
    }
}
