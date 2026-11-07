package sfz.nosql.l12

import java.util.PriorityQueue
import kotlin.random.Random

/** Given: squared Euclidean distance (pgvector's `<->` without the square root, which doesn't change the order). */
fun distance(a: FloatArray, b: FloatArray): Double {
    var sum = 0.0
    for (i in a.indices) {
        val d = (a[i] - b[i]).toDouble()
        sum += d * d
    }
    return sum
}

/** A vector's id (its position in the list) and its distance from the query. */
data class Neighbor(val id: Int, val distance: Double)

/** Given: the share of the true nearest neighbours that an approximate search found, |found ∩ truth| / |truth|. */
fun recall(found: List<Neighbor>, truth: List<Neighbor>): Double =
    found.map { it.id }.toSet().intersect(truth.map { it.id }.toSet()).size.toDouble() / truth.size

private val closestFirst = compareBy<Neighbor>({ it.distance }, { it.id })

/**
 * Exact nearest neighbours: compare the query with every vector. Always right, and the cost grows
 * with the number of vectors: a million vectors is a million distance computations per query.
 */
class ExactSearch(val vectors: List<FloatArray>) {
    /** How many distances have been computed so far. */
    var distanceCalls = 0L

    /** The [k] vectors closest to [query], closest first (ties by id). Count every distance you compute. */
    fun search(query: FloatArray, k: Int): List<Neighbor> = TODO("compute every distance (count them), sort by distance then id, take k")
}

/**
 * A proximity graph: every vector is linked to its nearest neighbours, plus a few random far links,
 * like one layer of HNSW. A search walks the graph from [entry] towards the query and looks at only
 * a small part of it. It can miss a true neighbour: that is the "approximate" in ANN.
 *
 * Your job: [search]. [build] is given.
 */
class GraphIndex(val vectors: List<FloatArray>, val links: List<IntArray>, val entry: Int) {
    /** How many distances have been computed so far. */
    var distanceCalls = 0L

    /**
     * Greedy beam search, the search HNSW runs on each layer, with a beam of [ef] (pgvector's `hnsw.ef_search`):
     *
     * 1. Compute the distance to [entry]. It starts both lists: `candidates` (to expand, closest first) and
     *    `best` (the closest [ef] seen so far). Mark it visited.
     * 2. Take the closest candidate. If it is farther than the worst of `best` and `best` already holds
     *    [ef] vectors, stop: nothing left can improve the result.
     * 3. Otherwise look at each of its [links] not yet visited: mark it, compute its distance, and if
     *    `best` has fewer than [ef] or it beats the worst of `best`, add it to both lists (drop the worst
     *    of `best` if it now has more than [ef]).
     * 4. Repeat from 2 until no candidates are left. Return the [k] closest of `best`, closest first.
     *
     * Count every distance you compute in [distanceCalls].
     */
    fun search(query: FloatArray, k: Int, ef: Int): List<Neighbor> {
        TODO("greedy beam search from entry with a beam of ef; count distances")
    }

    companion object {
        /**
         * Given: links every vector to its [m] nearest neighbours (found by brute force, both directions)
         * plus [far] random others, and enters at vector 0. Real HNSW builds its layers incrementally,
         * and much faster; the graph it ends up with is similar in spirit.
         */
        fun build(vectors: List<FloatArray>, m: Int = 8, far: Int = 2, random: Random = Random(42)): GraphIndex {
            val near = vectors.indices.map { i ->
                vectors.indices.filter { it != i }.sortedBy { distance(vectors[i], vectors[it]) }.take(m)
            }
            val links = vectors.indices.map { mutableSetOf<Int>() }
            near.forEachIndexed { i, ns -> ns.forEach { j -> links[i] += j; links[j] += i } }
            links.forEachIndexed { i, set -> repeat(far) { set += random.nextInt(vectors.size).takeIf { it != i } ?: ((i + 1) % vectors.size) } }
            return GraphIndex(vectors, links.map { it.toIntArray() }, entry = 0)
        }
    }
}
