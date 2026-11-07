package sfz.internals.l12

import java.util.PriorityQueue
import kotlin.random.Random

// The simulated network and clock that run a Raft cluster. Done for you.

/**
 * [size] Raft servers on a simulated network, driven by a simulated clock in milliseconds. Everything random
 * (election timeouts, message delays, which messages are lost) comes from [seed], so the same seed gives the
 * same run, message for message.
 *
 * Each message takes from [minDelay] to [maxDelay] ms and is lost with probability [lossRate]. A crashed
 * server ([crash]) neither sends nor receives; [restart] brings it back with its persistent state (term,
 * vote, log) and nothing else. An isolated server ([isolate]) keeps running, but every message to or from it
 * is lost until [heal]: a network partition.
 *
 * While it runs, the cluster records a timeline in [events] and checks Raft's safety rules after every
 * millisecond: at most one leader per term, a server never commits a different entry at an index someone
 * already committed, and a new leader holds every committed entry. Broken rules go to [violations].
 */
class Cluster(
    val size: Int = 5,
    seed: Long = 1,
    var lossRate: Double = 0.0,
    private val minDelay: Long = 1,
    private val maxDelay: Long = 10,
    timing: Timing = Timing(),
) {
    private class InFlight(val at: Long, val seq: Long, val from: Int, val to: Int, val msg: Message)

    private val network = Random(seed)
    private val queue = PriorityQueue<InFlight>(compareBy<InFlight>({ it.at }, { it.seq }))
    private var seq = 0L
    private val up = BooleanArray(size) { true }
    private val isolated = BooleanArray(size)

    /** The simulated time in milliseconds. */
    var now = 0L
        private set

    /** The timeline: elections, votes, commits, crashes, one line each. */
    val events = ArrayList<String>()

    /** Broken safety rules. A correct Raft never adds anything here. */
    val violations = ArrayList<String>()

    var messagesSent = 0L
        private set
    var messagesLost = 0L
        private set

    val nodes: List<RaftNode> = List(size) { id ->
        RaftNode(
            id, size, Random(seed * 1_000 + id), timing,
            send = { to, msg -> post(id, to, msg) },
            trace = { events += "t=%5d  %-3s %s".format(now, name(id), it) },
        )
    }

    // what the safety checks remember
    private val leaderOfTerm = HashMap<Long, Int>()
    private val committed = HashMap<Int, Entry>()         // index -> the entry committed there
    private val checkedUpTo = IntArray(size)              // per server: commit indexes already checked
    private val leaderCommitSeen = IntArray(size)

    init {
        nodes.forEach { it.start(0) }
    }

    fun isUp(id: Int) = up[id]

    /** The live leader with the highest term, or null. (A cut-off old leader may still think it leads.) */
    fun leader(): RaftNode? = nodes.filter { up[it.id] && !isolated[it.id] && it.role == Role.LEADER }.maxByOrNull { it.currentTerm }

    /** Gives [command] to the current leader. Returns its log index, or null if there is no leader. */
    fun propose(command: String): Int? = leader()?.let { proposeTo(it.id, command) }

    /** Gives [command] to server [id], leader or not, as a client that still believes in an old leader would. */
    fun proposeTo(id: Int, command: String): Int? {
        val index = nodes[id].propose(command) ?: return null
        note("client", "\"$command\" to ${name(id)}, appended at index $index in term ${nodes[id].currentTerm}")
        return index
    }

    fun crash(id: Int) {
        up[id] = false
        note(name(id), "crashes")
    }

    fun restart(id: Int) {
        up[id] = true
        nodes[id].restart(now)
        checkedUpTo[id] = 0
        leaderCommitSeen[id] = 0
        note(name(id), "restarts as a follower in term ${nodes[id].currentTerm} with ${nodes[id].lastLogIndex} log entries")
    }

    fun isolate(id: Int) {
        isolated[id] = true
        note(name(id), "is cut off from the network")
    }

    fun heal(id: Int) {
        isolated[id] = false
        note(name(id), "is reachable again")
    }

    /** Advances the clock by one millisecond: delivers the messages due, then lets every live server tick. */
    fun step() {
        now++
        while (queue.isNotEmpty() && queue.peek().at <= now) {
            val m = queue.poll()
            if (!up[m.to] || isolated[m.to]) continue
            val target = nodes[m.to]
            val before = if (m.msg is AppendEntries) target.log.toList() else null
            target.receive(m.from, m.msg, now)
            if (before != null) {                                    // did this AppendEntries cut the log?
                var same = 0
                while (same < before.size && same < target.log.size && before[same] == target.log[same]) same++
                if (same < before.size) {
                    note(name(m.to), "drops ${before.subList(same, before.size).joinToString(" ")} from index ${same + 1}: they conflict with ${name(m.from)}'s log")
                }
            }
        }
        for (n in nodes) if (up[n.id]) n.tick(now)
        checkSafety()
    }

    fun runFor(ms: Long) = repeat(ms.toInt()) { step() }

    /** Steps until [done] is true or [maxMs] pass. Returns whether [done] became true. */
    fun runUntil(maxMs: Long, done: (Cluster) -> Boolean): Boolean {
        val end = now + maxMs
        while (now < end) {
            if (done(this)) return true
            step()
        }
        return done(this)
    }

    /** The entries committed so far, by index, as the safety checks saw them. */
    fun committedEntries(): List<Entry> = (1..committed.size).mapNotNull { committed[it] }

    private fun note(who: String, what: String) {
        events += "t=%5d  %-3s %s".format(now, who, what)
    }

    private fun post(from: Int, to: Int, msg: Message) {
        messagesSent++
        if (isolated[from] || isolated[to] || network.nextDouble() < lossRate) {
            messagesLost++
            return
        }
        val delay = minDelay + if (maxDelay > minDelay) network.nextLong(maxDelay - minDelay + 1) else 0L
        queue += InFlight(now + delay, seq++, from, to, msg)
    }

    private fun checkSafety() {
        for (n in nodes) {
            if (!up[n.id]) continue
            if (n.commitIndex > n.lastLogIndex) violations += "t=$now ${name(n.id)} commit index ${n.commitIndex} is past its log"
            if (n.role == Role.LEADER) {
                val other = leaderOfTerm.putIfAbsent(n.currentTerm, n.id)
                if (other == null) {
                    // a new leader: it must hold every committed entry (leader completeness)
                    for ((i, e) in committed) if (i > n.lastLogIndex || n.log[i - 1] != e) {
                        violations += "t=$now new leader ${name(n.id)} lacks committed entry $i ($e)"
                    }
                } else if (other != n.id) {
                    violations += "t=$now two leaders in term ${n.currentTerm}: ${name(other)} and ${name(n.id)}"
                }
                if (n.commitIndex > leaderCommitSeen[n.id]) {
                    val from = leaderCommitSeen[n.id] + 1
                    val what = (from..n.commitIndex).joinToString(", ") { "${n.log[it - 1].command} at $it" }
                    note(name(n.id), "commits $what")
                }
            }
            leaderCommitSeen[n.id] = n.commitIndex
            // every newly committed index must hold the entry anyone else committed there (state machine safety)
            for (i in checkedUpTo[n.id] + 1..minOf(n.commitIndex, n.lastLogIndex)) {
                val e = n.log[i - 1]
                val before = committed.putIfAbsent(i, e)
                if (before != null && before != e) violations += "t=$now ${name(n.id)} committed $e at $i, but $before was committed there"
            }
            checkedUpTo[n.id] = maxOf(checkedUpTo[n.id], n.commitIndex)
        }
    }
}
