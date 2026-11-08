package sfz.model.l09

/** One statement: [s] (subject) [p] (predicate) [o] (object), such as `M-0042 ownedBy C-7`. */
data class Triple(val s: String, val p: String, val o: String)

/**
 * A triple pattern, the building block of a SPARQL query. Each position is either a constant,
 * such as `ownedBy`, or a variable, written with a leading `?`, such as `?owner`.
 */
data class Pattern(val s: String, val p: String, val o: String)

/** Variable name (with its `?`) to the value it is bound to. */
typealias Bindings = Map<String, String>

/** True for a variable such as `?owner`. */
fun isVariable(term: String): Boolean = term.startsWith("?")

/**
 * A tiny in-memory triple store: a set of triples, plus a basic graph pattern query,
 * which is what the `WHERE { ... }` of a SPARQL SELECT is.
 */
class TripleStore {
    private val triples = LinkedHashSet<Triple>()   // insertion order; a triple is stored once

    /** Adds one triple. Returns false if it was already there (a triple store is a set). */
    fun add(s: String, p: String, o: String): Boolean = triples.add(Triple(s, p, o))

    fun size(): Int = triples.size

    /**
     * Every way [pattern] matches a stored triple, as bindings that extend [given].
     *
     * For each stored triple, try to unify the three positions in order s, p, o:
     * 1. A constant must equal the triple's value in that position.
     * 2. A variable already bound (in [given], or earlier in this same pattern) must be bound
     *    to the triple's value.
     * 3. An unbound variable gets bound to the triple's value.
     * If all three positions unify, add the extended bindings to the result. Keep the order
     * in which the triples were added.
     *
     * Example: `Pattern("?c", "owns", "M-0042")` against `C-7 owns M-0042` gives `{?c=C-7}`.
     * `Pattern("?x", "owns", "?x")` matches only a triple whose subject equals its object.
     */
    fun match(pattern: Pattern, given: Bindings = emptyMap()): List<Bindings> {
        val out = ArrayList<Bindings>()
        for (t in triples) {
            var b: Bindings? = given
            // unify position by position; a failed position turns b into null
            b = unify(pattern.s, t.s, b)
            b = unify(pattern.p, t.p, b)
            b = unify(pattern.o, t.o, b)
            if (b != null) out += b
        }
        return out
    }

    private fun unify(term: String, value: String, b: Bindings?): Bindings? {
        if (b == null) return null                     // an earlier position already failed
        if (!isVariable(term)) return if (term == value) b else null   // rule 1: constants must match
        val bound = b[term] ?: return b + (term to value)              // rule 3: bind a free variable
        return if (bound == value) b else null                         // rule 2: a bound one must agree
    }

    /**
     * A basic graph pattern: every pattern must match, and a variable means the same value
     * wherever it appears. Given: it is a join, one pattern at a time, built on [match].
     */
    fun query(patterns: List<Pattern>): List<Bindings> =
        patterns.fold(listOf<Bindings>(emptyMap())) { rows, pattern -> rows.flatMap { match(pattern, it) } }
}
