package sfz.dist.l06

import java.util.PriorityQueue
import kotlin.math.ln
import kotlin.random.Random

// Causal histories for lesson dist-06 (given). A seeded generator plays N nodes for a while on virtual time: each node
// now and then does something local or sends a message to another node, and messages arrive after a random delay.
// Every node has its own wall clock: real time plus a fixed offset, so two clocks disagree by up to maxSkewMs, and a
// node can also have its clock stepped back (as NTP does when it corrects a clock that ran fast).

enum class Kind { LOCAL, SEND, RECEIVE }

/**
 * One event. [realTime] is the true time (no node can see it); [physical] is what the node's own wall clock read,
 * in milliseconds. For SEND, [msg] is the id of the message sent; for RECEIVE, the id of the message received.
 */
data class Event(val index: Int, val node: Int, val kind: Kind, val realTime: Long, val physical: Long, val msg: Int = -1)

/** A node's clock steps back by [byMs] at real time [atRealMs]. */
data class Step(val node: Int, val atRealMs: Long, val byMs: Long)

/** The events in real-time order, plus each node's clock offset. */
class History(val nodes: Int, val events: List<Event>, val offsets: List<Long>, val steps: List<Step>)

object Histories {
    /**
     * A history of [events] events on [nodes] nodes. Each node acts on average every [meanGapMs] ms; an action sends
     * a message to a random other node with probability [sendChance], otherwise it is local. A message takes a random
     * delay from [delayMs]. Clock offsets are drawn from 0..[maxSkewMs]. Same arguments, same history.
     */
    fun generate(
        seed: Long,
        nodes: Int = 4,
        events: Int = 200,
        maxSkewMs: Long = 10,
        delayMs: LongRange = 1L..20L,
        meanGapMs: Long = 5,
        sendChance: Double = 0.5,
        steps: List<Step> = emptyList(),
    ): History {
        require(nodes >= 2) { "a history needs at least two nodes" }
        val rnd = Random(seed)
        val offsets = List(nodes) { rnd.nextLong(0, maxSkewMs + 1) }
        fun gap() = (-meanGapMs * ln(1 - rnd.nextDouble())).toLong()
        fun physical(node: Int, real: Long) =
            real + offsets[node] - steps.filter { it.node == node && it.atRealMs <= real }.sumOf { it.byMs }

        val nextAction = LongArray(nodes) { gap() }
        class InFlight(val at: Long, val seq: Int, val to: Int, val msg: Int)
        val inFlight = PriorityQueue(compareBy<InFlight>({ it.at }, { it.seq }))
        var seq = 0
        var nextMsg = 0
        val out = mutableListOf<Event>()
        while (out.size < events) {
            val node = (0 until nodes).minBy { nextAction[it] }
            val arrival = inFlight.peek()
            if (arrival != null && arrival.at <= nextAction[node]) {          // a delivery comes first
                inFlight.poll()
                out += Event(out.size, arrival.to, Kind.RECEIVE, arrival.at, physical(arrival.to, arrival.at), arrival.msg)
                continue
            }
            val now = nextAction[node]
            if (rnd.nextDouble() < sendChance) {
                val to = (node + 1 + rnd.nextInt(nodes - 1)) % nodes
                val msg = nextMsg++
                inFlight += InFlight(now + rnd.nextLong(delayMs.first, delayMs.last + 1), seq++, to, msg)
                out += Event(out.size, node, Kind.SEND, now, physical(node, now), msg)
            } else {
                out += Event(out.size, node, Kind.LOCAL, now, physical(node, now))
            }
            nextAction[node] = now + gap()
        }
        return History(nodes, out, offsets, steps)
    }
}

/** A vector clock (given): one counter per node, as in the Replication track's lesson on concurrent writes. */
class VectorClock(val counts: IntArray) {
    /** True if this event happened before [other]: no entry larger, at least one smaller. */
    infix fun happenedBefore(other: VectorClock): Boolean {
        var smaller = false
        for (i in counts.indices) {
            if (counts[i] > other.counts[i]) return false
            if (counts[i] < other.counts[i]) smaller = true
        }
        return smaller
    }

    /** True if neither event happened before the other. */
    infix fun concurrentWith(other: VectorClock): Boolean =
        !(this happenedBefore other) && !(other happenedBefore this) && !counts.contentEquals(other.counts)

    override fun toString() = counts.joinToString(",", "[", "]")
}

/** The vector clock of every event, index for index: the exact happens-before relation, used to check the others. */
fun vectorStamps(h: History): List<VectorClock> {
    val current = Array(h.nodes) { IntArray(h.nodes) }
    val sent = HashMap<Int, IntArray>()
    return h.events.map { e ->
        val mine = current[e.node]
        if (e.kind == Kind.RECEIVE) {
            val theirs = sent.getValue(e.msg)
            for (i in mine.indices) mine[i] = maxOf(mine[i], theirs[i])
        }
        mine[e.node]++
        if (e.kind == Kind.SEND) sent[e.msg] = mine.copyOf()
        VectorClock(mine.copyOf())
    }
}

/** Every event's Lamport stamp, replaying [h] through one [LamportClock] per node. */
fun lamportStamps(h: History): List<Stamp> {
    val clocks = List(h.nodes) { LamportClock(it) }
    val sent = HashMap<Int, Stamp>()
    return h.events.map { e ->
        val clock = clocks[e.node]
        when (e.kind) {
            Kind.LOCAL -> clock.local()
            Kind.SEND -> clock.send().also { sent[e.msg] = it }
            Kind.RECEIVE -> clock.receive(sent.getValue(e.msg))
        }
    }
}

/** Every event's hybrid logical clock stamp, replaying [h] through one [HybridClock] per node. */
fun hlcStamps(h: History): List<Hlc> {
    var reading = 0L                                    // the wall clock of whichever node is acting now
    val clocks = List(h.nodes) { HybridClock(it) { reading } }
    val sent = HashMap<Int, Hlc>()
    return h.events.map { e ->
        reading = e.physical
        val clock = clocks[e.node]
        when (e.kind) {
            Kind.LOCAL -> clock.local()
            Kind.SEND -> clock.send().also { sent[e.msg] = it }
            Kind.RECEIVE -> clock.receive(sent.getValue(e.msg))
        }
    }
}
