package sfz.model.l09.demo

/**
 * Naive Datalog evaluation of
 *   controls(X, Y) :- owns(X, Y).
 *   controls(X, Z) :- controls(X, Y), owns(Y, Z).
 * on ownership chains of growing length. Every round joins ALL facts found so far.
 */
fun main() {
    println("companies  facts    rounds  derivations")
    for (n in listOf(50, 100, 200, 400)) {
        // C-1 owns C-2 owns C-3 ... owns C-n
        val owns = (1 until n).map { "C-$it" to "C-${it + 1}" }.toSet()
        val next = owns.groupBy({ it.first }, { it.second })
        var controls: Set<Pair<String, String>> = owns          // the first rule copies owns
        var derivations = owns.size.toLong()
        var rounds = 0
        while (true) {
            rounds++
            val derived = HashSet<Pair<String, String>>()
            for ((x, y) in controls) for (z in next[y].orEmpty()) { derived += x to z; derivations++ }
            val grown = controls + derived
            if (grown.size == controls.size) break               // a round that adds nothing: the fixpoint
            controls = grown
        }
        println("%9d  %6d  %6d  %,11d".format(n, controls.size, rounds, derivations))
    }
}
