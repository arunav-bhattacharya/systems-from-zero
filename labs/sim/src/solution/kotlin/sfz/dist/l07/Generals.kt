package sfz.dist.l07

/**
 * Lesson dist-07: one lying node and a majority vote.
 *
 * Node 0 is the leader. It has a verdict for a payment (approve or decline) and sends it to every
 * follower (nodes 1 to n - 1). Then every follower tells every other follower what the leader told
 * it. Each follower decides by majority over what it heard: the leader's message plus one relayed
 * message from each other follower. This is Lamport, Shostak and Pease's one-round algorithm for
 * one traitor, OM(1).
 *
 * Exactly one node lies, and it may say anything to anyone: a lying leader can tell different
 * followers different things, and a lying follower can relay a different verdict to each node.
 * Two rules must hold for the honest followers:
 * - agreement: they all decide the same verdict;
 * - validity: if the leader is honest, they decide the leader's verdict.
 */

enum class Verdict { APPROVE, DECLINE }

/** What a follower does when what it heard splits evenly. */
enum class Tie {
    /** Decide APPROVE. */
    APPROVE,

    /** Decide DECLINE. */
    DECLINE,

    /** Decide whatever the leader told this follower. */
    LEADER,
}

/**
 * Exercise 4 of 4: decide by majority.
 *
 * Count [fromLeader] and every verdict in [relayed]. If one verdict has strictly more votes, it
 * wins. On a tie, follow [tie]: a fixed verdict, or [fromLeader] for [Tie.LEADER].
 */
fun decide(fromLeader: Verdict, relayed: List<Verdict>, tie: Tie): Verdict {
    val approve = relayed.count { it == Verdict.APPROVE } + if (fromLeader == Verdict.APPROVE) 1 else 0
    val decline = relayed.size + 1 - approve
    return when {
        approve > decline -> Verdict.APPROVE
        decline > approve -> Verdict.DECLINE
        else -> when (tie) {
            Tie.APPROVE -> Verdict.APPROVE
            Tie.DECLINE -> Verdict.DECLINE
            Tie.LEADER -> fromLeader                       // depends on this follower's own view
        }
    }
}

/**
 * One round: what the honest leader would have said ([leaderSays]), which node lies ([liar]), the
 * lies it told in the order they were needed ([lies]), and what each honest follower decided.
 */
data class Round(
    val n: Int,
    val liar: Int,
    val leaderSays: Verdict,
    val lies: List<Verdict>,
    val decisions: Map<Int, Verdict>,
)

/** How many messages the liar sends: the leader sends one to each follower, a follower relays to the others. */
fun liesNeeded(n: Int, liar: Int): Int = if (liar == 0) n - 1 else n - 2

/** Runs one round of OM(1) with [n] nodes, node [liar] telling [lies] (given). */
fun round(n: Int, leaderSays: Verdict, liar: Int, lies: List<Verdict>, tie: Tie): Round {
    require(lies.size == liesNeeded(n, liar)) { "the liar sends ${liesNeeded(n, liar)} messages" }
    val lie = lies.iterator()
    val followers = 1 until n
    // step 1: the leader tells each follower its verdict
    val heardFromLeader = followers.associateWith { if (liar == 0) lie.next() else leaderSays }
    // step 2: each follower tells each other follower what the leader said
    val relayed = followers.associateWith { mutableListOf<Verdict>() }
    for (from in followers) {
        for (to in followers) {
            if (to == from) continue
            relayed.getValue(to) += if (from == liar) lie.next() else heardFromLeader.getValue(from)
        }
    }
    // step 3: every honest follower decides
    val decisions = followers.filter { it != liar }
        .associateWith { decide(heardFromLeader.getValue(it), relayed.getValue(it), tie) }
    return Round(n, liar, leaderSays, lies, decisions)
}

/** Which rule [r] breaks, or null if both hold (given). */
fun broken(r: Round): String? {
    if (r.decisions.values.toSet().size > 1) return "agreement: honest followers decided ${r.decisions}"
    if (r.liar != 0 && r.decisions.values.any { it != r.leaderSays }) {
        return "validity: the leader said ${r.leaderSays}, honest followers decided ${r.decisions}"
    }
    return null
}

/** Every combination of [k] verdicts. */
private fun allLies(k: Int): List<List<Verdict>> =
    (0 until (1 shl k)).map { bits -> (0 until k).map { if (bits shr it and 1 == 1) Verdict.APPROVE else Verdict.DECLINE } }

/** Every round with one liar: each verdict the leader could hold, each liar, every possible set of lies (given). */
fun allRounds(n: Int, tie: Tie): List<Round> =
    Verdict.entries.flatMap { says ->
        (0 until n).flatMap { liar -> allLies(liesNeeded(n, liar)).map { round(n, says, liar, it, tie) } }
    }

/** The first round with one liar that breaks agreement or validity, or null if none does (given). */
fun findViolation(n: Int, tie: Tie): Round? = allRounds(n, tie).firstOrNull { broken(it) != null }
