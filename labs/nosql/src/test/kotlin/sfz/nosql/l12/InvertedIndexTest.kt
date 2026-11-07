package sfz.nosql.l12

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test
import kotlin.math.ln

class InvertedIndexTest {
    // the merchant directory from the lesson's OpenSearch Try-it
    private val merchants = mapOf(
        "M-0042" to "Northwind Bikes, bike repairs and spare parts",
        "M-0043" to "Northwind Coffee",
        "M-0044" to "City Bike Rental",
        "M-0045" to "Bikes and Boards Outlet, used bikes",
        "M-0046" to "Harbour Fish Market",
    )

    private fun index() = InvertedIndex().apply { merchants.forEach { (id, name) -> add(id, name) } }

    @Test
    fun `tokenize is given and splits on punctuation, lower-cased`() {
        assertThat(tokenize("Northwind Bikes, bike repairs")).containsExactly("northwind", "bikes", "bike", "repairs")
    }

    @Test
    fun `add builds one posting per document per term, with the term frequency, and records lengths`() {
        val idx = index()
        assertThat(idx.postingList("bikes")).containsExactly(Posting("M-0042", 1), Posting("M-0045", 2))
        assertThat(idx.postingList("northwind").map { it.docId }).containsExactly("M-0042", "M-0043")
        assertThat(idx.postingList("scooter")).isEmpty()
        assertThat(idx.lengths).containsEntry("M-0042", 7).containsEntry("M-0043", 2).containsEntry("M-0046", 3)
        assertThat(idx.averageLength).isEqualTo(21 / 5.0)
    }

    @Test
    fun `a rare term scores higher than a common one`() {
        val idx = index()
        assertThat(idx.idf("fish")).isGreaterThan(idx.idf("northwind")) // 1 document against 2
        assertThat(idx.idf("fish")).isCloseTo(ln(1 + (5 - 1 + 0.5) / (1 + 0.5)), within(1e-12))
    }

    @Test
    fun `search adds up BM25 per query term, exactly as the formula says`() {
        val idx = index()
        val hits = idx.search("northwind bikes")
        // M-0042 has both terms; work its score out by hand from the posting lists
        val avg = 21 / 5.0
        fun part(term: String, tf: Int, len: Int) = idx.idf(term) * tf / (tf + 1.2 * (1 - 0.75 + 0.75 * len / avg))
        assertThat(hits.first().docId).isEqualTo("M-0042")
        assertThat(hits.first().score).isCloseTo(part("northwind", 1, 7) + part("bikes", 1, 7), within(1e-9))
        assertThat(hits.map { it.docId }).containsExactly("M-0042", "M-0043", "M-0045")
        // OpenSearch 3.9 returned exactly these scores for the same five merchants and the same query
        assertThat(hits.map { it.score }).zipSatisfy(listOf(0.62533486, 0.5064695, 0.4883092)) { a, b -> assertThat(a).isCloseTo(b, within(1e-6)) }
    }

    @Test
    fun `a short document beats a long one for the same single match, and documents without a query term never appear`() {
        val idx = index()
        // "northwind" once in each: M-0043 has 2 tokens, M-0042 has 7
        val hits = idx.search("northwind")
        assertThat(hits.map { it.docId }).containsExactly("M-0043", "M-0042")
        assertThat(idx.search("scooter")).isEmpty()
        assertThat(idx.search("bike bikes", k = 1)).hasSize(1)
    }

    @Test
    fun `ties are broken by document id, and k limits the results`() {
        val idx = InvertedIndex().apply {
            add("M-2", "fish market")
            add("M-1", "fish market")
            add("M-3", "harbour")
        }
        assertThat(idx.search("fish").map { it.docId }).containsExactly("M-1", "M-2")
        assertThat(idx.search("fish market harbour", k = 2).map { it.docId }).containsExactly("M-3", "M-1")
    }
}
