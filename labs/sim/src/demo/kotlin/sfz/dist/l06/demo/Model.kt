package sfz.dist.l06.demo

import java.util.PriorityQueue
import kotlin.math.ln
import kotlin.random.Random

// A copy of the lab's reference model (labs/sim/src/solution/kotlin/sfz/dist/l06), so the demos run
// without your exercises. Read the lab's files for the comments on each part.

// ---- from History.kt ----
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

// ---- from Lamport.kt ----
/** A Lamport timestamp: the counter, and the node that made it to break ties. */
data class Stamp(val counter: Long, val node: Int) : Comparable<Stamp> {
    // counter first; two nodes can reach the same counter, so the node id breaks the tie and the order is total
    override fun compareTo(other: Stamp): Int = compareValuesBy(this, other, Stamp::counter, Stamp::node)

    override fun toString() = "($counter,$node)"
}

/** One node's Lamport clock. No wall clock anywhere: it counts events. */
class LamportClock(val node: Int) {
    var counter = 0L
        private set

    /** A local event: count it. */
    fun local(): Stamp {
        counter++
        return Stamp(counter, node)
    }

    /** Sending is an event too; the stamp travels with the message. */
    fun send(): Stamp = local()

    /** Jump past anything the sender had counted, then count the receive itself. */
    fun receive(message: Stamp): Stamp {
        counter = maxOf(counter, message.counter) + 1
        return Stamp(counter, node)
    }
}

// ---- from Hybrid.kt ----
/**
 * A hybrid logical clock timestamp (Kulkarni et al., 2014): [l] is the largest wall-clock reading this node has
 * heard of, in milliseconds, and [c] counts events that share that [l].
 */
data class Hlc(val l: Long, val c: Int) : Comparable<Hlc> {
    override fun compareTo(other: Hlc): Int = compareValuesBy(this, other, Hlc::l, Hlc::c)   // given

    /** One Long: [l] in the top 48 bits, [c] in the low 16, so comparing the Longs compares the stamps. */
    fun pack(): Long = (l shl 16) or c.toLong()

    override fun toString() = "($l,$c)"

    companion object {
        const val MAX_C = 0xFFFF

        fun unpack(packed: Long): Hlc = Hlc(packed ushr 16, (packed and 0xFFFF).toInt())
    }
}

/** One node's hybrid logical clock. [physical] reads the node's own wall clock, in ms; it may jump back. */
class HybridClock(val node: Int, val physical: () -> Long) {
    var last = Hlc(0, 0)
        private set

    /** A local or send event (the paper's Figure 5, "send or local event"). */
    fun local(): Hlc {
        val pt = physical()
        val l = maxOf(last.l, pt)                        // follow the wall clock, but never go back
        val c = if (l == last.l) last.c + 1 else 0       // same l as before: count; the clock moved on: start at 0
        return set(l, c)
    }

    fun send(): Hlc = local()

    /** Receiving [m] (the paper's "receive event of message m"). */
    fun receive(m: Hlc): Hlc {
        val pt = physical()
        val l = maxOf(last.l, m.l, pt)                   // the largest time anyone in my past has seen
        val c = when {
            l == last.l && l == m.l -> maxOf(last.c, m.c) + 1
            l == last.l -> last.c + 1                    // my own l won
            l == m.l -> m.c + 1                          // the sender's l won: continue its count
            else -> 0                                    // my wall clock is ahead of both
        }
        return set(l, c)
    }

    private fun set(l: Long, c: Int): Hlc {
        check(c <= Hlc.MAX_C) { "the counter would overflow 16 bits" }
        last = Hlc(l, c)
        return last
    }
}

// ---- from Snowflake.kt ----
/**
 * A Snowflake-style id generator: 41 bits of milliseconds since [EPOCH_MS], 10 bits of machine id (0 to 1,023) and
 * 12 bits of sequence (4,096 ids per millisecond), in one positive Long. [clock] reads the wall clock in ms.
 */
class SnowflakeIds(val machine: Int, val clock: () -> Long) {
    init {
        require(machine in 0..MAX_MACHINE) { "machine id must fit in 10 bits" }
    }

    private var lastMs = -1L
    private var sequence = 0

    /** The next id: always larger than every id this generator has made, whatever the clock does. */
    fun next(): Long {
        var ms = maxOf(clock(), lastMs)               // the clock stepped back? keep using the last millisecond
        if (ms == lastMs) {
            sequence++
            if (sequence > MAX_SEQUENCE) {            // 4,096 ids in this millisecond already:
                ms = lastMs + 1                       // borrow the next one and run slightly ahead of the clock
                sequence = 0
            }
        } else {
            sequence = 0
        }
        lastMs = ms
        return compose(ms, machine, sequence)
    }

    companion object {
        /** 2026-01-01T00:00:00Z. Twitter's original used its own epoch in November 2010. */
        const val EPOCH_MS = 1_767_225_600_000L
        const val MAX_MACHINE = 0x3FF
        const val MAX_SEQUENCE = 0xFFF

        fun compose(ms: Long, machine: Int, sequence: Int): Long =
            ((ms - EPOCH_MS) shl 22) or (machine.toLong() shl 12) or sequence.toLong()

        fun timestampOf(id: Long): Long = (id ushr 22) + EPOCH_MS
        fun machineOf(id: Long): Int = ((id ushr 12) and 0x3FF).toInt()
        fun sequenceOf(id: Long): Int = (id and 0xFFF).toInt()
    }
}
