package sfz.dist.l07.demo

/**
 * Lesson dist-07, section 4: one liar against a majority vote, with 3, 4 and 5 nodes.
 *
 * Node 0 (the leader) sends its verdict for a payment to every follower; every follower relays what
 * it heard to every other follower; each follower takes the majority. One node lies, in every way it
 * can. The demo runs every such round and prints the first one that breaks a rule.
 * Run: ./gradlew :sim:demo -Pmain=sfz.dist.l07.demo.GeneralsDemoKt
 */
fun main() {
    println("%5s  %-8s %7s  %s".format("nodes", "on a tie", "rounds", "first round that breaks a rule"))
    for (n in 3..5) {
        for (tie in Tie.entries) {
            val rounds = allRounds(n, tie)
            val bad = rounds.firstOrNull { broken(it) != null }
            println("%5d  %-8s %7d  %s".format(n, tie.name.lowercase(), rounds.size, bad?.let(::describe) ?: "none"))
        }
    }
}

private fun describe(r: Round): String {
    val who = if (r.liar == 0) "the leader lies" else "follower ${r.liar} lies"
    return "$who (honest verdict ${r.leaderSays}): ${broken(r)!!.substringBefore(':')}, honest followers decide ${r.decisions}"
}
