package sfz.store.l08

import kotlin.math.ln

/**
 * Given: lower-case the text and split it on everything that isn't a letter or a digit. For plain
 * words like these, that is what OpenSearch's `standard` analyzer produces.
 */
fun tokenize(text: String): List<String> = text.lowercase().split(Regex("[^\\p{L}\\p{N}]+")).filter { it.isNotEmpty() }

/** One entry of a posting list: a document, and how many times the term occurs in it. */
data class Posting(val docId: String, val termFreq: Int)

/** One search result. */
data class Hit(val docId: String, val score: Double)

/**
 * An inverted index: for every term, the list of documents that contain it. Searching never reads
 * a document; it reads the posting lists of the query's terms and adds up a BM25 score per document.
 *
 * Your job: [add] and [search]. [idf] and the bookkeeping are given.
 */
class InvertedIndex(val k1: Double = 1.2, val b: Double = 0.75) {
    /** term -> its posting list, in the order the documents were added. */
    val postings: MutableMap<String, MutableList<Posting>> = HashMap()

    /** docId -> its length in tokens. */
    val lengths: MutableMap<String, Int> = LinkedHashMap()

    /** How many documents are indexed. */
    val docCount: Int get() = lengths.size

    /** The average document length in tokens. */
    val averageLength: Double get() = if (lengths.isEmpty()) 0.0 else lengths.values.sum().toDouble() / lengths.size

    /** The posting list of [term] (empty if no document has it). Given. */
    fun postingList(term: String): List<Posting> = postings[term].orEmpty()

    /**
     * Given: BM25's inverse document frequency, as Lucene computes it: `ln(1 + (N - n + 0.5) / (n + 0.5))`,
     * where N is [docCount] and n is how many documents contain [term]. Rare terms score high.
     */
    fun idf(term: String): Double {
        val n = postingList(term).size
        return ln(1 + (docCount - n + 0.5) / (n + 0.5))
    }

    /**
     * Indexes one document: [tokenize] the text, record its length in [lengths], and append one
     * `Posting(docId, count)` to the posting list of each DISTINCT term (count = occurrences in this document).
     */
    fun add(docId: String, text: String) {
        TODO("tokenize, record the length, append Posting(docId, count) per distinct term")
    }

    /**
     * Ranks documents for [query] with BM25 (Lucene's formula, which OpenSearch 3 uses by default):
     * for every query token, walk its posting list, and add to each document's score
     *
     *     idf(term) * tf / (tf + k1 * (1 - b + b * length / averageLength))
     *
     * where tf is the posting's term frequency and length is the document's length. Documents that
     * contain no query term are never touched. Return the [k] best, highest score first, ties by docId.
     */
    fun search(query: String, k: Int = 10): List<Hit> {
        TODO("for each query token walk its posting list and add idf * tf / (tf + k1 * (1 - b + b * len / avg))")
    }
}
