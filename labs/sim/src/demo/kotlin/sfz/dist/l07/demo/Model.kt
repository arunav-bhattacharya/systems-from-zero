package sfz.dist.l07.demo

/*
 * A copy of the lesson dist-07 reference model (the solution files Explorer.kt, Election.kt and
 * Generals.kt) for the demos. The lab exercises are in labs/sim/src/main/kotlin/sfz/dist/l07.
 */

// ---- from Explorer.kt ----
/**
 * Lesson dist-07: a tiny model checker. [explore] starts from the first state of a model, takes
 * every step the model allows from every state it reaches, and checks a safety rule (the
 * invariant) in each state. It goes breadth first, so the first broken state it meets is one of the
 * fewest steps from the start, and the trace it returns is a shortest way to break the rule. TLA+'s
 * model checker, TLC, does the same job on a written specification, with much better bookkeeping.
 *
 * A state must be an immutable value with a proper equals and hashCode (a data class of data
 * classes, lists, sets and maps), so that two paths reaching the same state count it once.
 */

/** What one exploration found. */
data class Exploration<S>(
    /** How many different states the explorer reached; a state reached by two paths counts once. */
    val states: Int,
    /** The step labels from the first state to a state that breaks the invariant, or null if none does. */
    val violation: List<String>?,
    /** The state that breaks the invariant, or null. */
    val badState: S?,
    /** Reached states where no step is possible and `done` is false: the system is stuck for good. */
    val stuck: Int,
)

/** Thrown when a model has more states than the explorer is willing to visit. */
class TooManyStates(limit: Int) : RuntimeException("more than $limit states: make the model smaller")

/**
 * The step labels that lead from the first state to [state], read back through [parent], which
 * maps every reached state to the state it was first reached from and the step taken (null for the
 * first state). Given.
 */
fun <S> traceTo(state: S, parent: Map<S, Pair<S, String>?>): List<String> {
    val steps = ArrayDeque<String>()
    var at = state
    while (true) {
        val (from, label) = parent.getValue(at) ?: break
        steps.addFirst(label)
        at = from
    }
    return steps.toList()
}

/**
 * Exercise 1 of 4: visit every state reachable from [initial], breadth first.
 *
 * Keep `parent`, a map from each state you have reached to how you first reached it (the previous
 * state and the step label; null for [initial]). It doubles as the visited set. Take states from
 * the front of a queue. For each one: if [invariant] is false, stop and return the trace to it
 * ([traceTo]) and the state itself. Otherwise ask [next] for its steps; if there are none and
 * [done] is false, count it as stuck. Put every state you have not seen before in `parent` and at
 * the back of the queue. Throw [TooManyStates] once `parent` holds more than [limit] states.
 *
 * When the queue is empty you have seen everything: return the number of states, no violation,
 * and the stuck count.
 */
fun <S> explore(
    initial: S,
    next: (S) -> List<Pair<String, S>>,
    invariant: (S) -> Boolean,
    done: (S) -> Boolean = { true },
    limit: Int = 2_000_000,
): Exploration<S> {
    val parent = HashMap<S, Pair<S, String>?>()            // also the set of states already seen
    val queue = ArrayDeque<S>()
    parent[initial] = null
    queue.addLast(initial)
    var stuck = 0
    while (queue.isNotEmpty()) {
        val s = queue.removeFirst()                        // breadth first: fewest steps first
        if (!invariant(s)) return Exploration(parent.size, traceTo(s, parent), s, stuck)
        val steps = next(s)
        if (steps.isEmpty() && !done(s)) stuck++           // nothing can ever happen here again
        for ((label, t) in steps) {
            if (t in parent) continue                      // reached before, by a path no longer
            parent[t] = s to label
            if (parent.size > limit) throw TooManyStates(limit)
            queue.addLast(t)
        }
    }
    return Exploration(parent.size, null, null, stuck)
}

// ---- from Election.kt ----
/**
 * Lesson dist-07: one election, checked against two node models.
 *
 * Three nodes (or five) elect a leader for one term. The first and last nodes are candidates: each
 * votes for itself and asks every other node for its vote. A node votes for the first candidate
 * that asks and refuses everyone after that. A candidate that collects votes from a majority has
 * won. The safety rule: at most one node ever wins the term.
 *
 * The network may hold any message for any time and deliver messages in any order. The explorer
 * tries every order, and every moment for a crash (at most [Election.maxCrashes] of them). A lost
 * message needs no step of its own: for safety it is the same as a message that is never
 * delivered, and the explorer looks at every state on the way to that.
 */

/** What a crash does to a node. */
enum class NodeModel {
    /** A crashed node never comes back. */
    CRASH_STOP,

    /** A crashed node may restart later. What it wrote to disk survives; everything in memory is gone. */
    CRASH_RECOVERY,
}

/** When a node writes its vote to disk. */
enum class Persist {
    /** Never: the vote lives only in memory. */
    NEVER,

    /** After the reply has gone out: a separate, later step writes it (a database that flushes every few seconds). */
    AFTER_REPLY,

    /** Before the reply goes out: by the time anyone hears of the vote, it is on disk. */
    BEFORE_REPLY,
}

/**
 * One node. [memVote] is the vote the running process knows about; [diskVote] is what a restart
 * would find on disk. [unflushed] is true while a vote is in memory but not yet on disk.
 * [votes] is, for a candidate, who has voted for it (memory only).
 */
data class Node(
    val name: String,
    val up: Boolean = true,
    val memVote: String? = null,
    val diskVote: String? = null,
    val unflushed: Boolean = false,
    val votes: Set<String> = emptySet(),
)

/** A message in flight. */
sealed interface Msg {
    val from: String
    val to: String
}

/** A candidate asks a node for its vote. */
data class RequestVote(override val from: String, override val to: String) : Msg {
    override fun toString() = "$from asks $to for its vote"
}

/** A node gives its vote to a candidate. */
data class Vote(override val from: String, override val to: String) : Msg {
    override fun toString() = "$from's vote reaches $to"
}

/**
 * The whole system at one moment: every node, every message in flight, how many crashes have
 * happened, and [elected], every node that has ever won this term. [elected] is the checker's
 * record of history, not any node's memory, so a crash can't erase it (a TLA+ spec calls this a
 * history variable).
 */
data class World(
    val nodes: List<Node>,
    val network: Set<Msg>,
    val crashes: Int = 0,
    val elected: Set<String> = emptySet(),
) {
    fun node(name: String): Node = nodes.first { it.name == name }
    fun with(node: Node): World = copy(nodes = nodes.map { if (it.name == node.name) node else it })
}

/**
 * Exercise 2 of 4: what a restart keeps.
 *
 * The process starts again with empty memory and reads the disk: it is up, it knows only the vote
 * that reached [Node.diskVote], nothing is waiting to be flushed, and a candidate has lost the
 * count of [Node.votes] it was holding in memory.
 */
fun recover(node: Node): Node =
    node.copy(up = true, memVote = node.diskVote, unflushed = false, votes = emptySet())

/**
 * Exercise 3 of 4: record a vote for [candidate].
 *
 * The node always remembers the vote in memory. With [Persist.BEFORE_REPLY] it also writes it to
 * disk now, before the reply is sent. With [Persist.AFTER_REPLY] it marks the vote [Node.unflushed]
 * and a later [flush] step writes it. With [Persist.NEVER] the disk never sees it.
 */
fun castVote(node: Node, candidate: String, persist: Persist): Node = when (persist) {
    Persist.NEVER -> node.copy(memVote = candidate)
    Persist.AFTER_REPLY -> node.copy(memVote = candidate, unflushed = true)   // the reply leaves before the disk write
    Persist.BEFORE_REPLY -> node.copy(memVote = candidate, diskVote = candidate) // on disk first, then the reply
}

/** The later disk write for [Persist.AFTER_REPLY] (given). */
fun flush(node: Node): Node = node.copy(diskVote = node.memVote, unflushed = false)

/** One election under one node model and one way of storing votes (given). */
class Election(
    val size: Int = 3,
    val model: NodeModel,
    val persist: Persist,
    val maxCrashes: Int = 1,
) {
    init {
        require(size >= 3) { "need at least three nodes" }
    }

    val names: List<String> = (1..size).map { "n$it" }
    val candidates: List<String> = listOf(names.first(), names.last())
    val majority: Int = size / 2 + 1

    /** Both candidates have voted for themselves and asked everyone else. */
    fun initial(): World {
        val nodes = names.map { name ->
            val node = Node(name)
            if (name in candidates) castVote(node, name, persist).copy(votes = setOf(name)) else node
        }
        val asks = candidates.flatMap { c -> names.filter { it != c }.map { RequestVote(c, it) } }
        return World(nodes, asks.toSet())
    }

    /** Every step possible from [w], with a label for the trace. */
    fun next(w: World): List<Pair<String, World>> {
        val steps = mutableListOf<Pair<String, World>>()
        for (m in w.network.sortedBy { it.toString() }) {
            if (!w.node(m.to).up) continue                 // waits in the network while its node is down
            steps += m.toString() to deliver(w, m)
        }
        for (n in w.nodes) {
            if (n.up && n.unflushed) steps += "${n.name} writes its vote to disk" to w.with(flush(n))
        }
        if (w.crashes < maxCrashes) {
            for (n in w.nodes) {
                if (n.up) steps += "${n.name} crashes" to w.with(n.copy(up = false)).copy(crashes = w.crashes + 1)
            }
        }
        if (model == NodeModel.CRASH_RECOVERY) {
            for (n in w.nodes) {
                if (!n.up) steps += "${n.name} restarts" to w.with(recover(n))
            }
        }
        return steps
    }

    private fun deliver(w: World, m: Msg): World {
        val rest = w.network - m
        return when (m) {
            is RequestVote -> {
                val voter = w.node(m.to)
                if (voter.memVote != null) {
                    w.copy(network = rest)                 // already voted (as far as it knows): refuse
                } else {
                    w.with(castVote(voter, m.from, persist)).copy(network = rest + Vote(m.to, m.from))
                }
            }
            is Vote -> {
                val candidate = w.node(m.to)
                val votes = candidate.votes + m.from
                val won = votes.size >= majority
                w.with(candidate.copy(votes = votes))
                    .copy(network = rest, elected = if (won) w.elected + candidate.name else w.elected)
            }
        }
    }

    /** The safety rule: at most one node ever wins the term. */
    fun oneLeader(w: World): Boolean = w.elected.size <= 1

    /** What liveness asks for: somebody has won. */
    fun someoneWon(w: World): Boolean = w.elected.isNotEmpty()

    /** Explore every reachable state of this election. */
    fun check(): Exploration<World> = explore(initial(), ::next, ::oneLeader, ::someoneWon)
}

// ---- from Generals.kt ----
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

