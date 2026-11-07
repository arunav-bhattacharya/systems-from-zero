package sfz.internals.l10

// Lesson 10 lab, part 1: estimate how many rows a WHERE clause keeps, from the statistics ANALYZE keeps.
// Your job: the bounds and fractionBelow() of EquiDepthHistogram, eq() and lt() of ColumnStats,
// and Selectivity.withDependency(). ColumnStats.analyze(), minMaxLt(), dependencyDegree() and
// Selectivity.independent() are done.

/**
 * An equi-depth histogram, the kind PostgreSQL keeps in `pg_stats.histogram_bounds`.
 *
 * [bounds] has `buckets + 1` values taken from the sorted column at evenly spaced POSITIONS, so every
 * bucket holds about the same number of rows. Where values are dense the buckets are narrow; where they
 * are sparse the buckets are wide. Bucket `i` covers the values from `bounds[i]` to `bounds[i + 1]`.
 */
class EquiDepthHistogram(sortedValues: LongArray, buckets: Int) {
    init {
        require(sortedValues.isNotEmpty()) { "no values" }
        require(buckets >= 1) { "need at least one bucket" }
    }

    /** `buckets + 1` bounds: `bounds[i]` is the value at position `(n - 1) * i / buckets` of the sorted values. */
    val bounds: LongArray = TODO("buckets + 1 values: bounds[i] = sortedValues[(n - 1) * i / buckets] (use Long math for the product)")

    val buckets: Int get() = bounds.size - 1

    /**
     * The fraction of the column's values that are below [v] (`col < v`), between 0.0 and 1.0.
     *
     * Find the bucket that holds [v], count the whole buckets before it, and assume the values inside that
     * bucket are spread evenly between its two bounds (the uniformity assumption). PostgreSQL's formula:
     * `(i + (v - bounds[i]) / (bounds[i + 1] - bounds[i])) / buckets`. Below the first bound: 0.0.
     * Above the last bound: 1.0.
     */
    fun fractionBelow(v: Long): Double {
        TODO("below bounds[0]: 0.0; above the last bound: 1.0; else find bucket i with bounds[i] < v <= bounds[i + 1] and return (i + (v - bounds[i]) / (bounds[i + 1] - bounds[i])) / buckets (a zero-width bucket counts as full)")
    }
}

/**
 * What ANALYZE stores for one column (PostgreSQL's `pg_stats` row), and the selectivity estimates the
 * planner computes from it. A selectivity is the fraction of rows a condition keeps: 0.02 means 2%.
 *
 * - [rows]: rows in the table.
 * - [distinct]: number of distinct values (`n_distinct`).
 * - [mcv]: the most common values and the fraction of ALL rows each one has
 *   (`most_common_vals`, `most_common_freqs`).
 * - [histogram]: an equi-depth histogram over the values that are NOT in [mcv], or null if there are none.
 * - [min], [max]: the smallest and largest value.
 */
class ColumnStats(
    val rows: Long,
    val distinct: Long,
    val mcv: Map<Long, Double>,
    val histogram: EquiDepthHistogram?,
    val min: Long,
    val max: Long,
) {
    /** The fraction of all rows that the most common values cover. */
    val mcvTotal: Double get() = mcv.values.sum()

    /**
     * Selectivity of `col = v`.
     *
     * If [v] is a most common value, its frequency is known: return it. Otherwise assume every other
     * distinct value is equally common (uniformity): the rows the MCVs don't cover, shared evenly by the
     * distinct values that aren't MCVs: `(1 - mcvTotal) / (distinct - mcv.size)`. 0.0 if there are none.
     */
    fun eq(v: Long): Double {
        TODO("an MCV: return its frequency; otherwise (1 - mcvTotal) / (distinct - mcv.size), or 0.0 if no other values exist")
    }

    /**
     * Selectivity of `col < v`: the most common values below [v] (their frequencies, summed), plus the share
     * of the other rows the histogram puts below [v]: `(1 - mcvTotal) * histogram.fractionBelow(v)`.
     */
    fun lt(v: Long): Double {
        TODO("sum the frequencies of the MCVs below v, then add (1 - mcvTotal) * histogram.fractionBelow(v) (0.0 if there is no histogram)")
    }

    /**
     * Selectivity of `col < v` with no histogram: assume the values are spread evenly between [min] and
     * [max]. This is the uniformity assumption applied to the whole column, for comparison.
     */
    fun minMaxLt(v: Long): Double = when {
        v <= min -> 0.0
        v > max -> 1.0
        else -> (v - min).toDouble() / (max - min)
    }

    companion object {
        /**
         * What ANALYZE computes, here over every value instead of a 30,000-row sample: the row count, the
         * number of distinct values, up to [mcvCount] most common values (only values more common than the
         * average value qualify), and an equi-depth histogram with [buckets] buckets over the rest.
         */
        fun analyze(values: LongArray, mcvCount: Int = 10, buckets: Int = 10): ColumnStats {
            require(values.isNotEmpty()) { "no values" }
            val counts = HashMap<Long, Int>()
            for (v in values) counts.merge(v, 1, Int::plus)
            val average = values.size.toDouble() / counts.size
            val common = counts.entries
                .filter { it.value > average * 1.25 }                         // clearly above average
                .sortedWith(compareByDescending<Map.Entry<Long, Int>> { it.value }.thenBy { it.key })
                .take(mcvCount)
                .associate { it.key to it.value.toDouble() / values.size }
            val rest = values.filter { it !in common }.sorted().toLongArray()
            return ColumnStats(
                rows = values.size.toLong(),
                distinct = counts.size.toLong(),
                mcv = common,
                histogram = if (rest.isEmpty()) null else EquiDepthHistogram(rest, minOf(buckets, rest.size)),
                min = values.min(),
                max = values.max(),
            )
        }
    }
}

/**
 * The degree of the functional dependency `a => b`, as ANALYZE computes it for
 * `CREATE STATISTICS ... (dependencies)`: group the rows by their `a` value; a group "supports" the
 * dependency if all its rows have the same `b`. The degree is supporting rows / all rows: 1.0 when `a`
 * always determines `b` (city => country), near 0.0 when it never does.
 */
fun dependencyDegree(a: LongArray, b: LongArray): Double {
    require(a.size == b.size && a.isNotEmpty()) { "columns of equal, non-zero length" }
    val bValuesPerA = HashMap<Long, MutableSet<Long>>()
    val rowsPerA = HashMap<Long, Int>()
    for (i in a.indices) {
        bValuesPerA.getOrPut(a[i]) { HashSet() } += b[i]
        rowsPerA.merge(a[i], 1, Int::plus)
    }
    val supporting = rowsPerA.entries.sumOf { (v, n) -> if (bValuesPerA.getValue(v).size == 1) n else 0 }
    return supporting.toDouble() / a.size
}

/** Combining the selectivities of two conditions on one table, `a = x AND b = y`. */
object Selectivity {
    /** The independence assumption: the fraction that passes both is the product. */
    fun independent(selA: Double, selB: Double): Double = selA * selB

    /**
     * PostgreSQL's formula when `b` depends on `a` with [degree] (from [dependencyDegree]):
     * `selA * (degree + (1 - degree) * selB)`. With degree 1, knowing `a` fixes `b`, so the answer is
     * `selA`; with degree 0 it is the independent product.
     */
    fun withDependency(selA: Double, selB: Double, degree: Double): Double =
        TODO("selA * (degree + (1 - degree) * selB)")
}
