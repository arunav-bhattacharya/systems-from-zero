package sfz.model.l09

/** One fact of a two-column relation, such as `owns(C-7, M-0042)`: [from] then [to]. */
data class Fact(val from: String, val to: String)

/**
 * What an evaluation produced, and what it cost.
 *
 * @param facts every derived `controls` fact
 * @param iterations rounds of the recursive rule, counting the last round, the one that found nothing new
 * @param derivations every fact the rules produced, duplicates included: the base rule's facts
 *   plus one per (controls, owns) pair the recursive rule joined. This is the work.
 */
data class Evaluation(val facts: Set<Fact>, val iterations: Int, val derivations: Long)

/**
 * Two Datalog rules over the base relation `owns(x, y)`, "x holds shares in y":
 *
 * ```
 * controls(X, Y) :- owns(X, Y).
 * controls(X, Z) :- controls(X, Y), owns(Y, Z).
 * ```
 *
 * The first rule copies every `owns` fact. The second, recursive rule says: if X controls Y and
 * Y owns Z, then X controls Z. Evaluating them means applying the rules until a round adds
 * nothing: the fixpoint. That is reachability in the ownership graph.
 */
object Reachability {

    /** For each company, the companies it owns: the index the recursive rule joins against. */
    private fun ownedBy(owns: Set<Fact>): Map<String, List<String>> =
        owns.groupBy({ it.from }, { it.to })

    /**
     * Naive evaluation. Given. Every round joins ALL the `controls` facts found so far with `owns`,
     * so round 10 re-derives everything rounds 1 to 9 already derived.
     */
    fun naive(owns: Set<Fact>): Evaluation {
        val next = ownedBy(owns)
        var controls: Set<Fact> = owns                    // base rule: controls(X, Y) :- owns(X, Y)
        var derivations = owns.size.toLong()
        var iterations = 0
        while (true) {
            iterations++
            val derived = HashSet<Fact>()
            for (c in controls) {                          // every fact so far, every round
                for (z in next[c.to].orEmpty()) {
                    derived += Fact(c.from, z)
                    derivations++
                }
            }
            val grown = controls + derived
            if (grown.size == controls.size) return Evaluation(controls, iterations, derivations)
            controls = grown
        }
    }

    /**
     * Semi-naive evaluation: the same rules and the same facts, less work.
     *
     * Keep `delta`, the facts that were new in the previous round. Start with delta = the base
     * facts (all of `owns`, counted as derivations). Each round, join only delta with `owns`:
     * count every pair joined as one derivation, and keep the results that aren't already known
     * as the next delta. Stop when a round's delta is empty; that round counts as an iteration.
     *
     * Why it's enough: a new fact needs a new ingredient. If neither `controls(X, Y)` nor
     * `owns(Y, Z)` changed since the last round, joining them again can only re-derive old facts.
     */
    fun semiNaive(owns: Set<Fact>): Evaluation {
        val next = ownedBy(owns)
        val controls = HashSet<Fact>(owns)                // everything known so far
        var delta: Set<Fact> = owns                        // what the last round added
        var derivations = owns.size.toLong()
        var iterations = 0
        while (delta.isNotEmpty()) {
            iterations++
            val fresh = HashSet<Fact>()
            for (c in delta) {                             // only last round's new facts
                for (z in next[c.to].orEmpty()) {
                    derivations++
                    val f = Fact(c.from, z)
                    if (f !in controls) fresh += f         // new this round
                }
            }
            controls += fresh
            delta = fresh
        }
        return Evaluation(controls, iterations, derivations)
    }
}
