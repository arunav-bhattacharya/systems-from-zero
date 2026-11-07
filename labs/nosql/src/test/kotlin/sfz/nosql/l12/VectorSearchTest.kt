package sfz.nosql.l12

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.random.Random

class VectorSearchTest {
    // 2,000 "embeddings" of 16 numbers in 40 clusters, like texts about 40 topics. Fixed seed.
    private val vectors: List<FloatArray>
    private val queries: List<FloatArray>

    init {
        val random = Random(2026)
        val centres = List(40) { FloatArray(16) { random.nextFloat() * 10 } }
        fun near(c: FloatArray) = FloatArray(16) { c[it] + (random.nextFloat() - 0.5f) * 3 }
        vectors = List(2_000) { near(centres[it % 40]) }
        queries = List(50) { near(centres[random.nextInt(40)]) }
    }

    private val index by lazy { GraphIndex.build(vectors) }

    @Test
    fun `exact search compares the query with every vector and returns the k closest, closest first`() {
        val exact = ExactSearch(vectors)
        val hits = exact.search(queries[0], 10)
        assertThat(hits).hasSize(10)
        assertThat(hits.map { it.distance }).isSorted()
        assertThat(exact.distanceCalls).isEqualTo(2_000)
        // nothing outside the result is closer than the 10th
        val tenth = hits.last().distance
        assertThat(vectors.indices.filter { it !in hits.map(Neighbor::id) }).allMatch { distance(queries[0], vectors[it]) >= tenth }
    }

    @Test
    fun `exact search breaks ties by id`() {
        val same = List(5) { FloatArray(2) { 1f } }
        assertThat(ExactSearch(same).search(FloatArray(2), 3).map { it.id }).containsExactly(0, 1, 2)
    }

    @Test
    fun `the graph search finds most true neighbours while computing far fewer distances`() {
        val exact = ExactSearch(vectors)
        val recalls = queries.map { q -> recall(index.search(q, 10, ef = 40), exact.search(q, 10)) }
        assertThat(recalls.average()).`as`("average recall@10 at ef = 40").isGreaterThan(0.85)
        assertThat(index.distanceCalls / queries.size).`as`("distances per query").isLessThan(1_000)
        assertThat(index.search(queries[0], 10, ef = 40).map { it.distance }).isSorted()
    }

    @Test
    fun `a bigger beam (ef) buys recall with more distance computations`() {
        val exact = ExactSearch(vectors)
        fun run(ef: Int): Pair<Double, Long> {
            val g = GraphIndex(vectors, index.links, index.entry)
            val r = queries.map { q -> recall(g.search(q, 10, ef), exact.search(q, 10)) }.average()
            return r to g.distanceCalls
        }
        val (small, smallCost) = run(10)
        val (big, bigCost) = run(200)
        assertThat(big).isGreaterThan(small)
        assertThat(big).isGreaterThan(0.97)
        assertThat(bigCost).isGreaterThan(smallCost)
    }

    @Test
    fun `the search returns at most k results and never the same vector twice`() {
        val hits = index.search(queries[3], k = 10, ef = 5)
        assertThat(hits.size).isLessThanOrEqualTo(10)
        assertThat(hits.map { it.id }).doesNotHaveDuplicates()
        val wide = index.search(queries[3], k = 10, ef = 50)
        assertThat(wide).hasSize(10)
        assertThat(wide.map { it.id }).doesNotHaveDuplicates()
    }
}
