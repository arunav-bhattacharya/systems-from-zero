package sfz.repl.l01

/**
 * Lesson repl-01: one leader, many followers. A model of single-leader replication on a simulated
 * network, in virtual time ([Sim]). The leader puts every write in its log with a position (1, 2,
 * 3...), ships each entry to the followers, and tells the client "OK" when the [Mode] says it may.
 * When the leader dies, [Cluster.failover] promotes a follower, and the tests count the
 * acknowledged writes the new leader never had.
 */

/** One write in the log: its position, the id the leader gave the new row, and the payment. */
data class LogEntry(val position: Long, val id: Long, val payment: String)

/** A copy of a node's table at one exact log position, as a base backup or a dump with its position. */
data class Snapshot(val position: Long, val rows: Map<Long, String>)

/** Thrown when a follower asks for entries the leader no longer keeps: rebuild it from a snapshot. */
class LogGoneException(message: String) : RuntimeException(message)

/** One database server, leader or follower. */
class Node(val name: String) {
    /** False once the node has crashed: it receives, applies and sends nothing. */
    var alive: Boolean = true

    /** The position of the last entry applied here: how far this copy has got. 0 is empty. */
    var position: Long = 0

    /** The table: row id to payment. */
    val rows: MutableMap<Long, String> = sortedMapOf()

    /** The entries this node has applied since its snapshot, oldest first. */
    val log: MutableList<LogEntry> = mutableListOf()

    /** The auto-increment counter: the id the next insert gets while this node is the leader. */
    var nextId: Long = 1

    /** A snapshot of the table, with the exact position it reflects (given). */
    fun snapshot(): Snapshot = Snapshot(position, rows.toMap())

    /** Replaces this node's data with [snapshot]; it then needs every entry after snapshot.position (given). */
    fun restore(snapshot: Snapshot) {
        rows.clear()
        rows.putAll(snapshot.rows)
        position = snapshot.position
        log.clear()
    }

    /** Throws away log entries at or before [position], as a leader does when it stops keeping old log (given). */
    fun truncateLogThrough(position: Long) {
        log.removeIf { it.position <= position }
    }

    /**
     * The entries after position [after], for a follower that is catching up (given). Throws
     * [LogGoneException] if some of them were already thrown away.
     */
    fun entriesAfter(after: Long): List<LogEntry> {
        val oldest = log.firstOrNull()?.position ?: (position + 1)
        if (after + 1 < oldest) {
            throw LogGoneException("$name: entries after $after are gone (oldest kept: $oldest); rebuild from a snapshot")
        }
        return log.filter { it.position > after }
    }

    /**
     * Exercise 1 of 3: apply entries in log order.
     *
     * Go through [entries] in order. Skip an entry this node already has (its position is at or
     * below [position]): resends happen after a reconnect. Apply the entry that comes next
     * (position == [position] + 1): put its row in [rows], append it to [log] and move [position]
     * to it. Stop at the first entry that would leave a gap (position > [position] + 1): something
     * in between never arrived, and applying out of order would make this copy a state the leader
     * never had. Return how many entries you applied.
     */
    fun apply(entries: List<LogEntry>): Int =
        TODO("apply the next entries in order: skip ones you have, stop at a gap")
}

/** When the leader tells the client "OK". */
sealed interface Mode {
    /** As soon as the entry is in the leader's own log. */
    data object Async : Mode

    /** Once [followers] followers have confirmed the entry. All of them is "fully synchronous". */
    data class Sync(val followers: Int) : Mode

    /**
     * MySQL-style semi-synchronous: once one follower has confirmed the entry, but wait at most
     * [timeoutMs]. After a timeout the leader carries on asynchronously until a follower catches up.
     */
    data class SemiSync(val timeoutMs: Long) : Mode
}

/** What a client was told: "OK" for [entry], asked at [sentAt], answered at [ackedAt]. */
data class Ack(val entry: LogEntry, val sentAt: Long, val ackedAt: Long) {
    val latencyMs: Long get() = ackedAt - sentAt
}

/** The outcome of a failover: the promoted follower, and the acknowledged writes it never had. */
data class FailoverResult(val newLeader: Node, val lost: List<Ack>)

/**
 * A leader and its followers on a simulated network (the plumbing is given; exercises 2 and 3 are
 * [isAcknowledged] and [failover]).
 *
 * [delays] maps each follower's name to the one-way network delay between it and the leader, in
 * milliseconds. Messages on one link arrive in the order they were sent, as on a TCP connection.
 * A message is lost if, when it arrives, its sender or receiver has crashed or the link is [cut].
 */
class Cluster(val sim: Sim, val mode: Mode, delays: Map<String, Long>) {
    val nodes: List<Node> = listOf(Node("leader")) + delays.keys.map(::Node)

    /** The node that takes writes now. */
    var leader: Node = nodes.first()
        private set

    /** Every node except the leader. */
    val followers: List<Node> get() = nodes.filter { it !== leader }

    /** One-way delay between the leader and each node, ms. Change it to slow a follower down. */
    val delayMs: MutableMap<String, Long> = delays.toMutableMap()

    /** Nodes whose link to the leader drops every message. */
    val cut: MutableSet<String> = mutableSetOf()

    /** The highest position each follower has confirmed to the current leader. */
    val confirmed: MutableMap<String, Long> = mutableMapOf()

    /** Every "OK" a client has received, in the order they were sent. */
    val acknowledged: MutableList<Ack> = mutableListOf()

    /**
     * Semi-synchronous only: false while the leader has fallen back to asynchronous. Setting it to
     * false records [switchedOffAt]; the leader sets it back to true once a follower confirms that
     * position (MySQL: "when at least one semisynchronous replica catches up").
     */
    var semiSyncOn: Boolean = true
        set(value) {
            if (field && !value) switchedOffAt = leader.position
            field = value
        }

    /** The leader's position when semi-sync last switched off. */
    var switchedOffAt: Long = 0
        private set

    private class Waiting(val entry: LogEntry, val sentAt: Long)

    private val waiting = mutableListOf<Waiting>()
    private val lastArrival = mutableMapOf<String, Long>()
    private val catchingUp = mutableSetOf<String>()

    private fun delayTo(node: Node): Long = delayMs[node.name] ?: 1

    /** A client writes [payment] to the leader now (given). It hears "OK" when [isAcknowledged] says so. */
    fun write(payment: String) {
        val l = leader
        if (!l.alive) return
        val entry = LogEntry(l.position + 1, l.nextId++, payment)
        l.rows[entry.id] = entry.payment
        l.log += entry
        l.position = entry.position
        for (f in followers) send(l, f, listOf(entry))
        waiting += Waiting(entry, sim.now)
        settle()
        if (mode is Mode.SemiSync) sim.after(mode.timeoutMs) { settle() }
    }

    /** Schedules writes of "pay-1", "pay-2"... every [everyMs] from [from] until [until] (given). */
    fun writeEvery(everyMs: Long, from: Long, until: Long) {
        var t = from
        var n = 1
        while (t <= until) {
            val name = "pay-${n++}"
            sim.at(t) { write(name) }
            t += everyMs
        }
    }

    /** [node] crashes now (given). If it was the leader, every client still waiting gets no answer. */
    fun crash(node: Node) {
        node.alive = false
        if (node === leader) waiting.clear()
    }

    /** Finds a node by name (given). */
    fun node(name: String): Node = nodes.first { it.name == name }

    private fun send(from: Node, to: Node, entries: List<LogEntry>) {
        if (to.name in cut) return
        val arrive = maxOf(sim.now + delayTo(to), lastArrival[to.name] ?: 0)
        lastArrival[to.name] = arrive
        sim.at(arrive) {
            if (!from.alive || !to.alive || to.name in cut || leader !== from) return@at
            to.apply(entries)
            val gap = entries.isNotEmpty() && to.position < entries.last().position
            if (gap) askForCatchUp(to, from)
            confirm(to, from, to.position)
        }
    }

    /** The follower asks for everything after its position; the leader sends it (given). */
    private fun askForCatchUp(follower: Node, from: Node) {
        if (!catchingUp.add(follower.name)) return
        val asked = follower.position
        sim.after(delayTo(follower)) {
            catchingUp.remove(follower.name)
            if (!from.alive || leader !== from || follower.name in cut) return@after
            send(from, follower, from.entriesAfter(asked))
        }
    }

    private fun confirm(follower: Node, to: Node, position: Long) {
        sim.after(delayTo(follower)) {
            if (!follower.alive || !to.alive || leader !== to || follower.name in cut) return@after
            confirmed[follower.name] = maxOf(confirmed[follower.name] ?: 0, position)
            if (mode is Mode.SemiSync && !semiSyncOn && position >= switchedOffAt) semiSyncOn = true
            settle()
        }
    }

    /** Answers every waiting client that [isAcknowledged] now allows, oldest first (given). */
    private fun settle() {
        if (!leader.alive) return
        val iterator = waiting.iterator()
        while (iterator.hasNext()) {
            val w = iterator.next()
            if (isAcknowledged(w.entry, sim.now - w.sentAt)) {
                acknowledged += Ack(w.entry, w.sentAt, sim.now)
                iterator.remove()
            }
        }
    }

    /**
     * Exercise 2 of 3: may the leader tell the client "OK" for [entry] yet?
     *
     * [waitedMs] is how long the client has been waiting. A follower "has" the entry when
     * confirmed[its name] is at least entry.position.
     *
     * - [Mode.Async]: yes, at once.
     * - [Mode.Sync]: yes once at least mode.followers of the current [followers] have it.
     * - [Mode.SemiSync]: yes if semi-sync is off ([semiSyncOn] false), or if any follower has it.
     *   Otherwise, if the client has waited mode.timeoutMs or longer, switch semi-sync off
     *   (semiSyncOn = false) and say yes: from now on the leader is asynchronous. Otherwise no.
     */
    fun isAcknowledged(entry: LogEntry, waitedMs: Long): Boolean =
        TODO("async: yes; sync: enough followers confirmed; semi-sync: one follower, or switch off after the timeout")

    /**
     * Exercise 3 of 3: the leader is dead; promote a follower.
     *
     * 1. Choose the live follower with the highest [Node.position] (the first in [followers] if
     *    several share it). Promoting a less up-to-date one loses more.
     * 2. Set its auto-increment counter the way a database does after promotion: one more than the
     *    highest row id it has (1 if it has no rows).
     * 3. The lost writes are the acknowledged ones whose entry position is beyond the new
     *    leader's position: their clients heard "OK", and the new leader has never seen them.
     * 4. Call [promote] with the chosen node, and return the result.
     */
    fun failover(): FailoverResult =
        TODO("choose the most up-to-date live follower, reset its id counter, list the lost acks, promote it")

    /**
     * Makes [node] the leader (given): writes go to it, confirmations start again from nothing, and
     * every other live node catches up from it.
     */
    fun promote(node: Node) {
        leader = node
        confirmed.clear()
        waiting.clear()
        lastArrival.clear()
        catchingUp.clear()
        semiSyncOn = true
        for (f in followers.filter { it.alive }) send(node, f, node.entriesAfter(minOf(f.position, node.position)))
    }
}
