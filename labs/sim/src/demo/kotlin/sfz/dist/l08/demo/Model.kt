package sfz.dist.l08.demo

/*
 * A copy of the lesson dist-08 reference model (the solution files Simulation.kt, PrimaryBackup.kt
 * and Dst.kt) for the demos. The lab exercises are in labs/sim/src/main/kotlin/sfz/dist/l08.
 */

import java.util.PriorityQueue
import kotlin.random.Random

// ---- from Simulation.kt ----
/**
 * Lesson dist-08: a deterministic simulation of a two-node, primary-backup register.
 *
 * Everything that could differ between two runs comes from one place: `Random(seed)`. It picks the
 * fault, the delay of every message, and nothing else is random. Time is virtual: [Simulation.now]
 * jumps from one event to the next, so a simulated second takes well under a millisecond, and
 * nothing ever sleeps. Run the same seed twice and you get the same events in the same order.
 *
 * The cast:
 * - n1 starts as the primary, n2 as its backup. The protocol under test decides everything they do.
 * - the client runs one operation at a time: write 1, read, write 2, read, and so on. It sends each
 *   one to whichever node the registry names as primary, and resends it there if no reply comes in
 *   [CLIENT_TIMEOUT_MS].
 * - the registry is service discovery: a node that promotes itself announces it, and the client
 *   uses the newest announcement.
 *
 * The fault model, which the lesson calls the simulator's system model: message delays of 1 to 10
 * ms, and at most one [Fault] per run, always on n1 or on the link between n1 and n2.
 *
 * After every event the simulation checks one rule with a god's-eye view of both nodes: the node
 * the registry calls primary holds a value at least as new as every acknowledged write. Values only
 * grow (write k stores k), so a smaller value means an acknowledged write is gone.
 */

const val CLIENT_TIMEOUT_MS = 50L
const val HEARTBEAT_EVERY_MS = 20L
const val FAILOVER_AFTER_MS = 100L
const val RESEND_EVERY_MS = 30L

/** The one fault a run may have. */
sealed interface Fault {
    /** Nothing goes wrong. */
    data object None : Fault

    /** n1 stops for [forMs] (a long GC pause, a VM stall): it handles nothing until it wakes. */
    data class Pause(val at: Long, val forMs: Long) : Fault

    /** n1 and n2 can't reach each other for [forMs]; the client still reaches both. */
    data class Cut(val at: Long, val forMs: Long) : Fault

    /** n1 stops for good. */
    data class Crash(val at: Long) : Fault

    companion object {
        /** A fault drawn from [rng]: none 40% of the time, else a pause, a cut or a crash. */
        fun random(rng: Random): Fault {
            val roll = rng.nextInt(10)
            return when {
                roll < 4 -> None
                roll < 6 -> Pause(rng.nextLong(100, 900), rng.nextLong(10, 300))
                roll < 8 -> Cut(rng.nextLong(100, 900), rng.nextLong(10, 300))
                else -> Crash(rng.nextLong(100, 900))
            }
        }
    }
}

/** Every message in the system. */
sealed interface Msg
data class Write(val op: Int, val value: Int) : Msg
data class Read(val op: Int) : Msg
data class Ack(val op: Int) : Msg
data class ReadOk(val op: Int, val value: Int) : Msg
data class Replicate(val op: Int, val value: Int, val epoch: Int) : Msg
data class ReplicateOk(val op: Int, val epoch: Int) : Msg
data class Heartbeat(val epoch: Int) : Msg
data class Refused(val epoch: Int) : Msg

/** What a server can do: the only doors from the protocol to the outside world. */
interface Env {
    val now: Long
    fun send(to: String, msg: Msg)

    /** Calls the node's onTimer([timer]) after [ms]. */
    fun after(ms: Long, timer: String)

    /** Tells the registry to send clients here. */
    fun announcePrimary()

    /** Adds a line to the trace. */
    fun log(text: String)
}

/** A replica. The simulation reads [value] and [isPrimary] to check the rule; only the protocol changes them. */
interface Server {
    val name: String
    val value: Int
    val isPrimary: Boolean
    fun start(env: Env)
    fun onMessage(from: String, msg: Msg)
    fun onTimer(timer: String)
}

/** Which protocol a run uses: the given naive one, or yours from PrimaryBackup.kt. */
enum class Protocol { NAIVE, FIXED }

/** One client operation as the client saw it, Jepsen style: invoked, then ok, or still unknown. */
data class Op(val op: Int, val kind: String, val value: Int?, val invokedAt: Long, val doneAt: Long?, val attempts: Int)

/** Everything a run produced. Two runs of one seed must be equal in every field. */
data class Run(
    val seed: Long,
    val protocol: Protocol,
    val fault: Fault,
    val trace: List<String>,
    val violation: String?,
    val history: List<Op>,
    val events: Int,
)

class Simulation(
    val seed: Long,
    val protocol: Protocol,
    fault: Fault? = null,
    val clientStopsAt: Long = 1_000,
    val endAt: Long = 1_500,
    /** Stop at the first violation (a search wants that), or run on to [endAt] (a history check wants the rest). */
    val stopAtViolation: Boolean = true,
) {
    private val rng = Random(seed)
    // draw a fault even when one is passed in, so the delays that follow come out the same either way
    private val drawn = Fault.random(rng)
    val fault: Fault = fault ?: drawn

    var now = 0L
        private set
    private val trace = mutableListOf<String>()
    private var violation: String? = null
    private var events = 0

    private class Event(val at: Long, val seq: Long, val node: String?, val action: () -> Unit)

    private var seq = 0L
    private val queue = PriorityQueue(compareBy<Event>({ it.at }, { it.seq }))
    private fun schedule(at: Long, node: String?, action: () -> Unit) {
        queue += Event(at, seq++, node, action)
    }

    private val servers: Map<String, Server> = when (protocol) {
        Protocol.NAIVE -> listOf(NaivePrimaryBackup("n1", "n2", true), NaivePrimaryBackup("n2", "n1", false))
        Protocol.FIXED -> listOf(PrimaryBackup("n1", "n2", true), PrimaryBackup("n2", "n1", false))
    }.associateBy { it.name }

    private var registry = "n1"
    private val down = mutableSetOf<String>()
    private val pausedUntil = mutableMapOf<String, Long>()
    private var cut = false

    private fun log(text: String) {
        trace += "%5d  %s".format(now, text)
    }

    /**
     * Exercise 2 of 3: make the run replay.
     *
     * Two runs of the same seed must produce the same trace. One line in this file draws a random
     * number without going through [rng], so every run differs. Find it and make it use [rng].
     *
     * Sends [msg] from [from] to [to]: dropped if the n1-n2 link is cut, otherwise delivered after
     * 1 to 10 ms.
     */
    private fun send(from: String, to: String, msg: Msg) {
        if (cut && setOf(from, to) == setOf("n1", "n2")) {
            log("$from -> $to $msg  DROPPED (link cut)")
            return
        }
        val delay = rng.nextLong(1, 11)                    // every random choice comes from the seed
        schedule(now + delay, to) {
            log("$from -> $to $msg")
            if (to == "client") client.onMessage(msg) else servers.getValue(to).onMessage(from, msg)
        }
    }

    private fun envFor(name: String) = object : Env {
        override val now get() = this@Simulation.now
        override fun send(to: String, msg: Msg) = send(name, to, msg)
        override fun after(ms: Long, timer: String) = schedule(this@Simulation.now + ms, name) {
            servers.getValue(name).onTimer(timer)
        }
        override fun announcePrimary() {
            registry = name
            log("registry: clients now go to $name")
        }
        override fun log(text: String) = this@Simulation.log("$name: $text")
    }

    /** The client: one operation at a time, resent to the registry's primary on every timeout. */
    private val client = object {
        val history = mutableListOf<Op>()
        var current: Op? = null
        var nextValue = 1
        var nextOp = 1

        fun startNext() {
            if (now >= clientStopsAt) return
            val op = nextOp++
            val kind = if (op % 2 == 1) "write" else "read"
            val value = if (kind == "write") nextValue++ else null
            current = Op(op, kind, value, now, null, 0)
            attempt()
        }

        fun attempt() {
            val c = current ?: return
            current = c.copy(attempts = c.attempts + 1)
            val msg = if (c.kind == "write") Write(c.op, c.value!!) else Read(c.op)
            send("client", registry, msg)
            val attempts = c.attempts + 1
            schedule(now + CLIENT_TIMEOUT_MS, "client") {
                val still = current
                if (still != null && still.op == c.op && still.attempts == attempts) attempt()
            }
        }

        fun onMessage(msg: Msg) {
            val c = current ?: return
            when {
                msg is Ack && msg.op == c.op -> finish(c.copy(doneAt = now))
                msg is ReadOk && msg.op == c.op -> finish(c.copy(value = msg.value, doneAt = now))
            }
        }

        fun finish(done: Op) {
            history += done
            current = null
            schedule(now + 5, "client") { startNext() }
        }
    }

    private val highestAcked get() = client.history.filter { it.kind == "write" }.maxOfOrNull { it.value!! } ?: 0

    /** The god's-eye rule, checked after every event. */
    private fun check() {
        if (violation != null) return
        val primary = servers.getValue(registry)
        if (primary.value < highestAcked) {
            violation = "at $now ms ${primary.name} is the primary and holds ${primary.value}, " +
                "but write $highestAcked was acknowledged"
            log("VIOLATION: $violation")
        }
    }

    /** Runs to [endAt] (or to the first violation, see [stopAtViolation]) and returns what happened. */
    fun run(): Run {
        log("seed $seed, protocol $protocol, fault $fault")
        for ((name, s) in servers) schedule(0, name) { s.start(envFor(name)) }
        schedule(1, "client") { client.startNext() }
        when (val f = fault) {
            Fault.None -> {}
            is Fault.Pause -> schedule(f.at, null) {
                pausedUntil["n1"] = f.at + f.forMs
                log("n1 PAUSED until ${f.at + f.forMs}")
            }
            is Fault.Cut -> {
                schedule(f.at, null) { cut = true; log("link n1-n2 CUT") }
                schedule(f.at + f.forMs, null) { cut = false; log("link n1-n2 healed") }
            }
            is Fault.Crash -> schedule(f.at, null) { down += "n1"; log("n1 CRASHED") }
        }
        while (queue.isNotEmpty() && (violation == null || !stopAtViolation)) {
            val e = queue.poll()
            if (e.at > endAt) break
            now = e.at
            if (e.node != null && e.node in down) continue                 // a crashed node does nothing
            val wake = e.node?.let { pausedUntil[it] }
            if (wake != null && now < wake) {                             // a paused node does it later
                schedule(wake, e.node, e.action)
                continue
            }
            events++
            e.action()
            check()
        }
        return Run(seed, protocol, fault, trace.toList(), violation, client.history.toList(), events)
    }
}

/**
 * Jepsen's view: only the client's history, no access to the servers. Returns every read that
 * returned a value older than a write the client had already seen acknowledged when it sent the
 * read (given).
 */
fun staleReads(history: List<Op>): List<String> {
    val stale = mutableListOf<String>()
    for (read in history.filter { it.kind == "read" }) {
        val newestAcked = history
            .filter { it.kind == "write" && it.doneAt != null && it.doneAt < read.invokedAt }
            .maxOfOrNull { it.value!! } ?: continue
        if (read.value!! < newestAcked) stale += "read ${read.op} returned ${read.value} after write $newestAcked was acknowledged"
    }
    return stale
}

// ---- from PrimaryBackup.kt ----
/**
 * Lesson dist-08: primary-backup replication of one register, twice.
 *
 * [NaivePrimaryBackup] is given and stays as it is: the simulator finds its bug. [PrimaryBackup] is
 * yours to fix (exercise 3).
 *
 * The design both share:
 * - the primary applies a client write, sends Replicate to the backup, and acknowledges the client
 *   only when the backup confirms (synchronous replication). It resends Replicate every
 *   [RESEND_EVERY_MS] until it hears back.
 * - the primary sends a heartbeat every [HEARTBEAT_EVERY_MS]. A backup that hears nothing from the
 *   primary for [FAILOVER_AFTER_MS] promotes itself, announces itself to the registry, and from then
 *   on runs alone: it treats its peer as dead and acknowledges writes itself.
 * - only a primary answers clients. A node that isn't primary ignores client requests, and the
 *   client's timeout sends them elsewhere.
 */
class NaivePrimaryBackup(
    override val name: String,
    private val peer: String,
    startsAsPrimary: Boolean,
) : Server {
    override var value = 0
        private set
    override var isPrimary = startsAsPrimary
        private set
    private var alone = false                              // promoted: the peer is presumed dead
    private var lastHeard = 0L
    private val waiting = mutableMapOf<Int, Int>()         // op -> value, waiting for the backup's ok
    private lateinit var env: Env

    override fun start(env: Env) {
        this.env = env
        env.after(HEARTBEAT_EVERY_MS, "heartbeat")
        env.after(10, "check")
    }

    override fun onMessage(from: String, msg: Msg) {
        if (from == peer) lastHeard = env.now
        when (msg) {
            is Write -> if (isPrimary) {
                value = msg.value
                if (alone) {
                    env.send("client", Ack(msg.op))
                } else {
                    waiting[msg.op] = msg.value
                    env.send(peer, Replicate(msg.op, msg.value, 1))
                    env.after(RESEND_EVERY_MS, "resend ${msg.op}")
                }
            }
            is Read -> if (isPrimary) env.send("client", ReadOk(msg.op, value))
            is Replicate -> {
                value = msg.value                          // the bug: whoever sends it, whatever we are now
                env.send(peer, ReplicateOk(msg.op, msg.epoch))
            }
            is ReplicateOk -> if (waiting.remove(msg.op) != null) env.send("client", Ack(msg.op))
            is Heartbeat, is Refused, is Ack, is ReadOk -> {}
        }
    }

    override fun onTimer(timer: String) {
        when {
            timer == "heartbeat" -> {
                if (isPrimary) env.send(peer, Heartbeat(1))
                env.after(HEARTBEAT_EVERY_MS, "heartbeat")
            }
            timer == "check" -> {
                if (!isPrimary && env.now - lastHeard > FAILOVER_AFTER_MS) {
                    isPrimary = true
                    alone = true
                    env.log("heard nothing from $peer for $FAILOVER_AFTER_MS ms: promoting myself")
                    env.announcePrimary()
                }
                env.after(10, "check")
            }
            timer.startsWith("resend ") -> {
                val op = timer.removePrefix("resend ").toInt()
                val v = waiting[op] ?: return
                env.send(peer, Replicate(op, v, 1))
                env.after(RESEND_EVERY_MS, timer)
            }
        }
    }
}

/**
 * Exercise 3 of 3: fence the old primary with epochs.
 *
 * The naive protocol's bug: when n1 pauses (or loses its link to n2) for longer than the failover
 * timeout, n2 promotes itself and acknowledges new writes. When n1 comes back it still believes it
 * is primary, and its late Replicate for an old write overwrites n2's newer value.
 *
 * The fix is a fencing token, as in lesson 5 of this track:
 * - every node keeps an [epoch], starting at 1. A node that promotes itself adds 1.
 * - every Replicate and Heartbeat carries the sender's epoch.
 * - a node that receives a Replicate or Heartbeat from an older epoch refuses it: it applies nothing
 *   and answers `Refused(myEpoch)`.
 * - a node that sees a newer epoch in any message from its peer (Replicate, Heartbeat, Refused)
 *   takes that epoch, and if it was primary it steps down: no longer primary, and it forgets the
 *   writes it was waiting to acknowledge. Log the step-down with `env.log("... steps down")`.
 */
class PrimaryBackup(
    override val name: String,
    private val peer: String,
    startsAsPrimary: Boolean,
) : Server {
    override var value = 0
        private set
    override var isPrimary = startsAsPrimary
        private set
    var epoch = 1
        private set
    private var alone = false
    private var lastHeard = 0L
    private val waiting = mutableMapOf<Int, Int>()
    private lateinit var env: Env

    override fun start(env: Env) {
        this.env = env
        env.after(HEARTBEAT_EVERY_MS, "heartbeat")
        env.after(10, "check")
    }

    /** A message from the peer carries [theirs]: true if it may be applied (same epoch). */
    private fun admit(theirs: Int): Boolean {
        if (theirs < epoch) {
            env.send(peer, Refused(epoch))                 // a deposed primary: tell it so, apply nothing
            return false
        }
        if (theirs > epoch) {
            epoch = theirs                                 // someone was promoted after us
            if (isPrimary) {
                isPrimary = false
                waiting.clear()                            // never acknowledge these now
                env.log("saw epoch $theirs: steps down")
            }
        }
        lastHeard = env.now
        return true
    }

    override fun onMessage(from: String, msg: Msg) {
        when (msg) {
            is Write -> if (isPrimary) {
                value = msg.value
                if (alone) {
                    env.send("client", Ack(msg.op))
                } else {
                    waiting[msg.op] = msg.value
                    env.send(peer, Replicate(msg.op, msg.value, epoch))
                    env.after(RESEND_EVERY_MS, "resend ${msg.op}")
                }
            }
            is Read -> if (isPrimary) env.send("client", ReadOk(msg.op, value))
            is Replicate -> if (admit(msg.epoch)) {
                value = msg.value
                env.send(peer, ReplicateOk(msg.op, epoch))
            }
            is Heartbeat -> admit(msg.epoch)
            is Refused -> if (msg.epoch > epoch) admit(msg.epoch)
            is ReplicateOk -> if (msg.epoch == epoch && waiting.remove(msg.op) != null) env.send("client", Ack(msg.op))
            is Ack, is ReadOk -> {}
        }
    }

    override fun onTimer(timer: String) {
        when {
            timer == "heartbeat" -> {
                if (isPrimary) env.send(peer, Heartbeat(epoch))
                env.after(HEARTBEAT_EVERY_MS, "heartbeat")
            }
            timer == "check" -> {
                if (!isPrimary && env.now - lastHeard > FAILOVER_AFTER_MS) {
                    isPrimary = true
                    alone = true
                    epoch += 1                             // the new token, larger than any the old primary has
                    env.log("heard nothing from $peer for $FAILOVER_AFTER_MS ms: promoting myself, epoch $epoch")
                    env.announcePrimary()
                }
                env.after(10, "check")
            }
            timer.startsWith("resend ") -> {
                val op = timer.removePrefix("resend ").toInt()
                val v = waiting[op] ?: return
                env.send(peer, Replicate(op, v, epoch))
                env.after(RESEND_EVERY_MS, timer)
            }
        }
    }
}

// ---- from Dst.kt ----
/**
 * Lesson dist-08: deterministic simulation testing. Run the simulation for seed after seed, stop at
 * the first that breaks the rule, and keep the seed: it is a complete, exact recipe for the failure.
 */
object Dst {
    /**
     * Exercise 1 of 3: find the first failing seed.
     *
     * Run `Simulation(seed, protocol, faultFor?.invoke(seed)).run()` for each seed in [seeds], in
     * order, and return the first [Run] whose violation isn't null. Return null if every seed
     * passes. When [faultFor] is null, each run draws its own fault from its seed.
     */
    fun search(seeds: LongRange, protocol: Protocol, faultFor: ((Long) -> Fault)? = null): Run? {
        for (seed in seeds) {
            val run = Simulation(seed, protocol, faultFor?.invoke(seed)).run()
            if (run.violation != null) return run          // the seed is the whole bug report
        }
        return null
    }

    /** Runs [run]'s seed again, with the same protocol and fault (given). */
    fun replay(run: Run): Run = Simulation(run.seed, run.protocol, run.fault).run()
}

