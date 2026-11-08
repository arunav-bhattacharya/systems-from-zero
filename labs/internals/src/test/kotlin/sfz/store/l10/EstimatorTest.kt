package sfz.store.l10

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.offset
import org.junit.jupiter.api.Test
import kotlin.math.abs
import kotlin.math.pow

class EstimatorTest {
    /** 100,000 payment amounts in cents, from 0 to 100,000, most of them small: x cubed for x uniform in [0, 1). */
    private val skewedAmounts = LongArray(100_000) { i -> (100_000 * (((i * 104_729L) % 100_000) / 100_000.0).pow(3)).toLong() }

    private fun truthLt(values: LongArray, v: Long) = values.count { it < v }.toDouble() / values.size

    @Test
    fun `an equi-depth histogram puts the same number of rows in every bucket`() {
        val uniform = EquiDepthHistogram(LongArray(1_000) { it + 1L }, 10)
        assertThat(uniform.bounds).containsExactly(1, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000)

        val sorted = skewedAmounts.sortedArray()
        val h = EquiDepthHistogram(sorted, 10)
        assertThat(h.bounds.first()).isEqualTo(sorted.first())
        assertThat(h.bounds.last()).isEqualTo(sorted.last())
        val firstWidth = h.bounds[1] - h.bounds[0]
        val lastWidth = h.bounds[10] - h.bounds[9]
        assertThat(lastWidth).`as`("dense small amounts get narrow buckets, sparse big ones get wide buckets")
            .isGreaterThan(50 * firstWidth)
    }

    @Test
    fun `fractionBelow counts whole buckets and interpolates inside one`() {
        val h = EquiDepthHistogram(LongArray(1_000) { it + 1L }, 10)
        assertThat(h.fractionBelow(250)).isCloseTo(0.25, offset(1e-9))   // 2 buckets + half of the third
        assertThat(h.fractionBelow(150)).isCloseTo(0.15, offset(1e-9))
        assertThat(h.fractionBelow(1)).isEqualTo(0.0)
        assertThat(h.fractionBelow(-5)).isEqualTo(0.0)
        assertThat(h.fractionBelow(1_000)).isCloseTo(1.0, offset(1e-9))
        assertThat(h.fractionBelow(5_000)).isEqualTo(1.0)
    }

    @Test
    fun `a range estimate on evenly spread values is within one percent`() {
        val values = LongArray(100_000) { (it * 7_919L) % 100_000 }
        val stats = ColumnStats.analyze(values, buckets = 10)
        assertThat(stats.mcv).`as`("every value appears once: nothing is common").isEmpty()
        for (v in 0L..100_000L step 997) {
            assertThat(stats.lt(v)).`as`("col < $v").isCloseTo(truthLt(values, v), offset(0.01))
        }
    }

    @Test
    fun `on skewed values the histogram stays close where a min-max line is far off`() {
        val stats = ColumnStats.analyze(skewedAmounts, buckets = 100)
        var worstHistogram = 0.0
        var worstMinMax = 0.0
        for (v in 500L..99_500L step 500) {
            val truth = truthLt(skewedAmounts, v)
            worstHistogram = maxOf(worstHistogram, abs(stats.lt(v) - truth))
            worstMinMax = maxOf(worstMinMax, abs(stats.minMaxLt(v) - truth))
        }
        assertThat(worstHistogram).`as`("worst error of the histogram estimate").isLessThan(0.01)
        assertThat(worstMinMax).`as`("worst error assuming values spread evenly from min to max").isGreaterThan(0.3)
    }

    /** 100,000 merchants: city 0 has 30%, city 1 has 20%, cities 2 to 41 share the other 50% (1.25% each). */
    private val cities = LongArray(100_000) { i ->
        when {
            i < 30_000 -> 0L
            i < 50_000 -> 1L
            else -> 2L + (i - 50_000) / 1_250
        }
    }

    @Test
    fun `an equality uses the MCV frequency, and spreads the rest evenly over the other values`() {
        val stats = ColumnStats.analyze(cities)
        assertThat(stats.distinct).isEqualTo(42)
        assertThat(stats.mcv.keys).containsExactlyInAnyOrder(0L, 1L)
        assertThat(stats.eq(0)).isCloseTo(0.30, offset(1e-9))
        assertThat(stats.eq(1)).isCloseTo(0.20, offset(1e-9))
        assertThat(stats.eq(7)).`as`("(1 - 0.5) / (42 - 2)").isCloseTo(0.0125, offset(1e-9))
        assertThat(stats.eq(99)).`as`("a value that isn't there still gets the average share").isCloseTo(0.0125, offset(1e-9))
    }

    @Test
    fun `a range adds the common values below it to the histogram's share of the rest`() {
        val stats = ColumnStats.analyze(cities)
        assertThat(stats.lt(0)).isEqualTo(0.0)
        assertThat(stats.lt(1)).`as`("only city 0, an MCV").isCloseTo(0.30, offset(1e-9))
        assertThat(stats.lt(3)).`as`("cities 0, 1 and 2").isCloseTo(truthLt(cities, 3), offset(0.02))
        assertThat(stats.lt(22)).isCloseTo(truthLt(cities, 22), offset(0.02))
        assertThat(stats.lt(1_000)).isCloseTo(1.0, offset(1e-9))
    }

    @Test
    fun `multiplying selectivities works for independent columns`() {
        val n = 100_000
        val currency = LongArray(n) { (it % 10).toLong() }            // 10 values
        val channel = LongArray(n) { ((it / 10) % 8).toLong() }       // 8 values, unrelated to currency
        val truth = (0 until n).count { currency[it] == 3L && channel[it] == 5L }.toDouble() / n
        val estimate = Selectivity.independent(ColumnStats.analyze(currency).eq(3), ColumnStats.analyze(channel).eq(5))
        assertThat(estimate).isCloseTo(truth, offset(truth * 0.1))
    }

    @Test
    fun `multiplying selectivities underestimates correlated columns ten times`() {
        val n = 100_000
        val city = LongArray(n) { (it % 10).toLong() }                // Amsterdam = 0, London = 1, ...
        val country = LongArray(n) { (it % 10).toLong() }             // NL = 0, GB = 1, ...: fixed by the city
        val truth = (0 until n).count { city[it] == 0L && country[it] == 0L }.toDouble() / n
        val estimate = Selectivity.independent(ColumnStats.analyze(city).eq(0), ColumnStats.analyze(country).eq(0))
        assertThat(truth).isCloseTo(0.1, offset(1e-9))
        assertThat(truth / estimate).`as`("actual / estimated rows").isGreaterThanOrEqualTo(9.0)
    }

    @Test
    fun `a functional dependency fixes the estimate for correlated columns`() {
        val n = 100_000
        val city = LongArray(n) { (it % 10).toLong() }
        val country = LongArray(n) { (it % 10).toLong() }
        val channel = LongArray(n) { ((it / 10) % 8).toLong() }
        assertThat(dependencyDegree(city, country)).isEqualTo(1.0)
        assertThat(dependencyDegree(city, channel)).isEqualTo(0.0)

        val selCity = ColumnStats.analyze(city).eq(0)
        val selCountry = ColumnStats.analyze(country).eq(0)
        val fixed = Selectivity.withDependency(selCity, selCountry, dependencyDegree(city, country))
        assertThat(fixed).isCloseTo(0.1, offset(0.005))
        assertThat(Selectivity.withDependency(0.1, 0.125, 0.0)).`as`("degree 0 is the independent product")
            .isCloseTo(0.0125, offset(1e-12))
        assertThat(Selectivity.withDependency(0.1, 0.1, 0.5)).isCloseTo(0.1 * (0.5 + 0.5 * 0.1), offset(1e-12))
    }

    @Test
    fun `a join estimate multiplies rows and the selectivities of the predicates inside the set`() {
        assertThat(joinSelectivity(10_000, 10_000)).isEqualTo(1.0 / 10_000)
        assertThat(joinSelectivity(9_948, 10_000)).`as`("the column with more distinct values decides").isEqualTo(1.0 / 10_000)
        val g = paymentsGraph()
        assertThat(g.estimate(0b001)).isEqualTo(10.0)
        assertThat(g.estimate(0b011)).`as`("merchants JOIN payments").isCloseTo(1_000.0, offset(1e-6))
        assertThat(g.estimate(0b110)).`as`("payments JOIN chargebacks").isCloseTo(20_000.0, offset(1e-6))
        assertThat(g.estimate(0b101)).`as`("no predicate: every pair").isCloseTo(200_000.0, offset(1e-6))
        assertThat(g.estimate(0b111)).isCloseTo(20.0, offset(1e-9))
        val fk = JoinGraph(listOf(Table("payments", 1e6), Table("merchants", 1e4)), listOf(Edge(0, 1, joinSelectivity(10_000, 10_000))))
        assertThat(fk.estimate(0b11)).`as`("a foreign key join returns one row per child row").isCloseTo(1e6, offset(1e-3))
    }

    /** merchants WHERE city = 'Amsterdam' AND country = 'NL' AND currency = 'EUR' (estimated 10 rows), payments, chargebacks. */
    private fun paymentsGraph() = JoinGraph(
        listOf(Table("merchants", 10.0), Table("payments", 1_000_000.0), Table("chargebacks", 20_000.0)),
        listOf(Edge(0, 1, 1.0 / 10_000), Edge(1, 2, 1.0 / 1_000_000)),
    )

    /** What running the query really produces: there are 1,000 such merchants, not 10. */
    private val actualRows = mapOf(0b001 to 1_000.0, 0b010 to 1_000_000.0, 0b100 to 20_000.0, 0b011 to 100_000.0, 0b110 to 20_000.0, 0b101 to 20_000_000.0, 0b111 to 2_000.0)

    @Test
    fun `dynamic programming picks the join order with the smallest intermediate result`() {
        val g = paymentsGraph()
        val plan = bestPlan(g)
        assertThat(plan.describe(g)).isEqualTo("((merchants JOIN payments) JOIN chargebacks)")
        assertThat(plan.cost).`as`("1,000 rows from the first join + 20 from the second").isCloseTo(1_020.0, offset(1e-6))
        assertThat(plan.rows).isCloseTo(20.0, offset(1e-9))
    }

    @Test
    fun `a 100x underestimate picks a plan that does more than four times the work`() {
        val g = paymentsGraph()
        val chosen = bestPlan(g)                                   // on the estimates
        val ideal = bestPlan(g) { actualRows.getValue(it) }        // on the real counts
        assertThat(ideal.describe(g)).isEqualTo("((payments JOIN chargebacks) JOIN merchants)")
        assertThat(ideal.cost).isCloseTo(22_000.0, offset(1e-6))
        val actualCostOfChosen = chosen.costWith { actualRows.getValue(it) }
        assertThat(actualCostOfChosen).isCloseTo(102_000.0, offset(1e-6))
        assertThat(actualCostOfChosen / ideal.cost).isGreaterThan(4.0)
    }

    @Test
    fun `dynamic programming finds the cheapest of all join trees, never with a cross product`() {
        val rnd = kotlin.random.Random(10)
        repeat(40) { round ->
            val n = rnd.nextInt(3, 7)
            val tables = List(n) { Table("t$it", 10.0.pow(rnd.nextDouble(1.0, 6.0))) }
            val edges = ArrayList<Edge>()
            for (t in 1 until n) edges += Edge(rnd.nextInt(t), t, 10.0.pow(-rnd.nextDouble(0.0, 5.0)))   // a random tree...
            repeat(rnd.nextInt(0, 3)) {                                                                    // ...plus a few more
                val a = rnd.nextInt(n)
                val b = rnd.nextInt(n)
                if (a != b) edges += Edge(a, b, 10.0.pow(-rnd.nextDouble(0.0, 5.0)))
            }
            val g = JoinGraph(tables, edges)
            val plan = bestPlan(g)
            assertThat(plan.set).isEqualTo(g.all)
            assertThat(plan.cost).`as`("round $round").isCloseTo(cheapestTree(g, g.all), offset(cheapestTree(g, g.all) * 1e-9))
            assertNoCrossProducts(g, plan)
        }
        val disconnected = JoinGraph(listOf(Table("a", 1.0), Table("b", 1.0), Table("c", 1.0)), listOf(Edge(0, 1, 0.5)))
        assertThat(runCatching { bestPlan(disconnected) }.exceptionOrNull())
            .`as`("c joins nothing").isInstanceOf(IllegalArgumentException::class.java)
    }

    /** Brute force: the cheapest cost over every join tree of [set] without cross products, bushy ones included. */
    private fun cheapestTree(g: JoinGraph, set: Int): Double {
        if (Integer.bitCount(set) == 1) return 0.0
        var best = Double.POSITIVE_INFINITY
        var left = (set - 1) and set
        while (left > 0) {
            val right = set xor left
            if (g.connects(left, right)) {
                val l = cheapestTree(g, left)
                val r = cheapestTree(g, right)
                if (l.isFinite() && r.isFinite()) best = minOf(best, l + r + g.estimate(set))
            }
            left = (left - 1) and set
        }
        return best
    }

    private fun assertNoCrossProducts(g: JoinGraph, p: Plan) {
        if (p is Join) {
            assertThat(g.connects(p.left.set, p.right.set)).`as`("a join of two sets no predicate connects").isTrue()
            assertNoCrossProducts(g, p.left)
            assertNoCrossProducts(g, p.right)
        }
    }
}
