package sfz.dist.l07

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
