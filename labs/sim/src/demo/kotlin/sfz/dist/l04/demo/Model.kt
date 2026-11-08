package sfz.dist.l04.demo

import java.util.PriorityQueue
import kotlin.math.ln
import kotlin.random.Random

// A copy of the lab's reference model (labs/sim/src/solution/kotlin/sfz/dist/l04), so the demos run
// without your exercises. Read the lab's files for the comments on each part.

// ---- from Sim.kt ----
/**
 * Virtual time for lesson dist-04 (given). Nothing here sleeps. [runUntil] runs the scheduled events in time order
 * and moves [now] from one to the next, so ten simulated minutes take a few milliseconds and every run with the same
 * seed gives exactly the same answer. Times are milliseconds.
 *
 * Every event has the time it runs ([at]) and the time it was due. They differ only for a paused process: a step due
 * during the pause runs when the pause ends. Events at the same time run in the order they were due, then in the
 * order they were scheduled, so when a pause ends the process catches up oldest step first.
 */
class Sim {
    var now: Long = 0
        private set

    private class Event(val at: Long, val due: Long, val seq: Long, val action: () -> Unit)

    private var seq = 0L
    private val queue = PriorityQueue(compareBy<Event>({ it.at }, { it.due }, { it.seq }))

    /** Runs [action] at [time]. [due] is when it was meant to run (the same, unless a pause pushed it back). */
    fun at(time: Long, due: Long = time, action: () -> Unit) {
        require(time >= now) { "time $time is in the past (now $now)" }
        queue += Event(time, due, seq++, action)
    }

    /** Runs every event scheduled at or before [time], then sets the clock to [time]. */
    fun runUntil(time: Long) {
        while (queue.isNotEmpty() && queue.peek().at <= time) {
            val event = queue.poll()
            now = event.at
            event.action()
        }
        if (time > now) now = time
    }
}

// ---- from World.kt ----
// The world of lesson dist-04 (given). Two holders, "A" and "B", compete for one lease that guards merchant M-0042's
// ledger. A lease service grants the lease and a ledger stores every write it receives. Neither of those ever pauses:
// only the holders do. The ledger checks nothing, which is the point: this lab measures the damage, and the next
// lesson makes the ledger refuse it.

/** One lease as the lease service saw it after the run: who held it, from when, and when it finally ran out. */
data class Lease(val id: Int, val holder: String, val grantedAt: Long, val expiresAt: Long) {
    /** The service treats the lease as valid from [grantedAt] up to, but not including, [expiresAt]. */
    fun validAt(t: Long): Boolean = t >= grantedAt && t < expiresAt
}

/** One write as the ledger saw it: who sent it, under which lease, when it left the holder and when it landed. */
data class Write(val holder: String, val leaseId: Int, val sentAt: Long, val landedAt: Long)

/** A stop-the-world pause of one holder: nothing in that process runs from [startMs] until [endMs]. */
data class Pause(val startMs: Long, val lengthMs: Long) {
    val endMs: Long get() = startMs + lengthMs
}

/** What a run produced. [writes] is in the order the ledger applied them; [log] is filled only if Scenario.log. */
class RunResult(
    val writes: List<Write>,
    val leases: Map<Int, Lease>,
    val pauses: Map<String, List<Pause>>,
    val log: List<String>,
)

/** The knobs of one run. The defaults are the lesson's numbers. */
data class Scenario(
    val seed: Int = 1,
    val durationMs: Long = 600_000,              // ten minutes of virtual time
    val ttlMs: Long = 2_000,                     // a lease, and each renewal, lasts 2 s (Jepsen's etcd test used 2 s)
    val renewBelowMs: Long = 1_000,              // a holder renews when it believes less than this is left
    val tickMs: Long = 100,                      // each holder runs its loop every 100 ms
    val workMs: Long = 60,                       // building one ledger update takes 60 ms after the check
    val sendMs: Long = 5,                        // serializing the write and handing it to the socket takes 5 ms
    val latencyMs: LongRange = 2L..8L,           // one-way network delay, picked at random for each message
    val pauseMs: Long = 0,                       // the length of every random pause; 0 means no random pauses
    val meanPauseGapMs: Long = 5_000,            // random pauses start on average this far apart, on each holder
    val pauses: Map<String, List<Pause>>? = null, // explicit pauses per holder ("A", "B"); replaces the random ones
    val log: Boolean = false,                    // record a readable timeline in RunResult.log
)

/** Runs [scenario] with both holders using [policy]. Same scenario, same result, every time. */
fun simulate(scenario: Scenario, policy: HolderPolicy): RunResult = World(scenario, policy).run()

private class World(val s: Scenario, val policy: HolderPolicy) {
    val sim = Sim()
    val network = Random(s.seed)
    val service = LeaseService(s.ttlMs)
    val writes = mutableListOf<Write>()
    val log = mutableListOf<String>()
    val pauses: Map<String, List<Pause>> = s.pauses
        ?: mapOf("A" to randomPauses(1), "B" to randomPauses(2))

    fun run(): RunResult {
        val a = Holder("A", phase = 0, pauses["A"].orEmpty().sortedBy { it.startMs }, this)
        val b = Holder("B", phase = 50, pauses["B"].orEmpty().sortedBy { it.startMs }, this)
        if (s.log) for ((who, list) in pauses) for (p in list) {
            sim.at(p.startMs) { note("$who stops: a %,d ms pause begins".format(p.lengthMs)) }
            sim.at(p.endMs, due = p.startMs) { note("$who runs again, and has no idea it stopped") }
        }
        a.start()
        b.start()
        sim.runUntil(s.durationMs)
        return RunResult(writes.toList(), service.leases.toMap(), pauses, log.toList())
    }

    fun note(line: String) {
        if (s.log) log += "%,7d ms  %s".format(sim.now, line)
    }

    fun latency(): Long = network.nextLong(s.latencyMs.first, s.latencyMs.last + 1)

    /** A message to the lease service or the ledger: they never pause, so it is handled when it arrives. */
    fun toServer(action: () -> Unit) = sim.at(sim.now + latency(), action = action)

    /** A message to a holder: it waits in the socket until the holder runs again. */
    fun toHolder(h: Holder, action: () -> Unit) = h.step(sim.now + latency(), action)

    fun land(w: Write) {
        writes += w
        if (s.log) {
            val lease = service.leases.getValue(w.leaseId)
            val verdict = if (lease.validAt(sim.now)) "inside its lease"
            else "AFTER its lease ran out at %,d ms".format(lease.expiresAt)
            note("ledger applies ${w.holder}'s update under lease ${w.leaseId}, $verdict")
        }
    }

    private fun randomPauses(stream: Int): List<Pause> {
        if (s.pauseMs <= 0) return emptyList()
        val rnd = Random(s.seed * 1_000 + stream)
        val out = mutableListOf<Pause>()
        var t = 0L
        while (true) {
            val gap = (-s.meanPauseGapMs * ln(1 - rnd.nextDouble())).toLong()   // exponential gaps: pauses at random
            val start = t + gap
            if (start >= s.durationMs) break
            out += Pause(start, s.pauseMs)
            t = start + s.pauseMs + 1
        }
        return out
    }
}

/** The lease service: one lease at a time, a new id for every grant, renewals only while the lease is valid. */
private class LeaseService(val ttlMs: Long) {
    val leases = LinkedHashMap<Int, Lease>()
    private var current: Lease? = null

    fun acquire(holder: String, t: Long): Int? {
        val c = current
        if (c != null && c.validAt(t)) return null                 // someone holds it (maybe the asker itself)
        val lease = Lease(leases.size + 1, holder, t, t + ttlMs)    // ids grow with every grant
        leases[lease.id] = lease
        current = lease
        return lease.id
    }

    fun renew(id: Int, t: Long): Boolean {
        val c = current
        if (c == null || c.id != id || !c.validAt(t)) return false  // too late: it ran out, or someone else has it
        val renewed = c.copy(expiresAt = t + ttlMs)
        leases[id] = renewed
        current = renewed
        return true
    }
}

/**
 * One lease holder: a loop that runs every tick. It renews when it believes less than renewBelowMs is left, and while
 * it holds the lease it checks, works for workMs, and writes. Every step goes through [step], so a step due during a
 * pause runs when the pause ends, and the code inside can't tell.
 */
private class Holder(val name: String, val phase: Long, val pauses: List<Pause>, val w: World) {
    private var leaseId: Int? = null
    private var believedExpiry = Long.MIN_VALUE
    private var waiting = false

    fun start() = step(phase) { tick() }

    /** The time a step due at [t] really runs: the end of the pause that covers [t], if any. */
    fun resume(t: Long): Long {
        var r = t
        for (p in pauses) if (r >= p.startMs && r < p.endMs) r = p.endMs
        return r
    }

    fun step(due: Long, action: () -> Unit) = w.sim.at(resume(due), due, action)

    private fun tick() {
        val now = w.sim.now
        val id = leaseId
        if (id != null && now >= believedExpiry) {
            w.note("$name sees that lease $id has run out")
            dropLease()
        }
        val held = leaseId
        if (held == null) {
            if (!waiting) acquire(sentAt = now)
        } else {
            if (!waiting && believedExpiry - now < w.s.renewBelowMs) renew(held, sentAt = now)
            if (w.policy.mayStartWork(now, believedExpiry)) work(held, checkedAt = now)
        }
        step(now + w.s.tickMs) { tick() }
    }

    private fun work(id: Int, checkedAt: Long) {
        step(checkedAt + w.s.workMs) {
            val expiry = if (leaseId == id) believedExpiry else Long.MIN_VALUE
            if (!w.policy.maySendWrite(w.sim.now, expiry)) {
                w.note("$name drops its update: the check before sending failed")
                return@step
            }
            step(w.sim.now + w.s.sendMs) {
                val sentAt = w.sim.now
                w.toServer { w.land(Write(name, id, sentAt, w.sim.now)) }
            }
        }
    }

    private fun acquire(sentAt: Long) {
        waiting = true
        w.toServer {
            val granted = w.service.acquire(name, w.sim.now)
            w.toHolder(this) {
                waiting = false
                if (granted != null) {
                    leaseId = granted
                    believedExpiry = w.policy.believedExpiry(sentAt, w.sim.now, w.s.ttlMs)
                    w.note("$name holds lease $granted and believes it lasts until %,d ms".format(believedExpiry))
                }
            }
        }
    }

    private fun renew(id: Int, sentAt: Long) {
        waiting = true
        w.toServer {
            val ok = w.service.renew(id, w.sim.now)
            w.toHolder(this) {
                waiting = false
                if (leaseId != id) return@toHolder
                if (ok) {
                    believedExpiry = w.policy.believedExpiry(sentAt, w.sim.now, w.s.ttlMs)
                    w.note("$name renewed lease $id and believes it lasts until %,d ms".format(believedExpiry))
                } else {
                    w.note("$name is told lease $id is gone")
                    dropLease()
                }
            }
        }
    }

    private fun dropLease() {
        leaseId = null
        believedExpiry = Long.MIN_VALUE
    }
}

// ---- from Policy.kt ----
/**
 * How a lease holder decides, using only what it can see: its own clock and the replies it has handled. Here that
 * clock is the simulator's, which is monotonic and exact, so lesson 3's clock problems are switched off and every
 * stale write you count comes from a pause.
 */
interface HolderPolicy {
    /**
     * When the holder believes its lease ends, after a grant or a renewal. [sentAt] is when it sent the request,
     * [handledAt] when its code handled the reply, [ttlMs] the lease length.
     */
    fun believedExpiry(sentAt: Long, handledAt: Long, ttlMs: Long): Long

    /** Checked at the start of each tick, before the work. */
    fun mayStartWork(now: Long, believedExpiry: Long): Boolean

    /** Checked when the work is done, right before the write is serialized and sent. */
    fun maySendWrite(now: Long, believedExpiry: Long): Boolean
}

/** The holder from the lesson's first section (given). It is wrong on purpose, in two ways. */
object Naive : HolderPolicy {
    // counts the lease from the moment it handled the reply: a reply that waited out a pause looks fresh
    override fun believedExpiry(sentAt: Long, handledAt: Long, ttlMs: Long) = handledAt + ttlMs

    // checks once, at the start of the tick
    override fun mayStartWork(now: Long, believedExpiry: Long) = now < believedExpiry

    // and never looks again before the write leaves
    override fun maySendWrite(now: Long, believedExpiry: Long) = true
}

/** The mitigations a holder can apply on its own. They shrink the damage; the lab measures how far. */
class Careful(val marginMs: Long) : HolderPolicy {
    // The service started the lease when the request arrived, which is after sentAt. Counting from sentAt can only
    // make the holder's deadline earlier than the real one, however long the reply waited in the socket.
    override fun believedExpiry(sentAt: Long, handledAt: Long, ttlMs: Long) = sentAt + ttlMs

    // Don't start work that the margin doesn't cover.
    override fun mayStartWork(now: Long, believedExpiry: Long) = believedExpiry - now >= marginMs

    // Look again after the work, as late as possible: a pause during the work is caught here. A pause after this
    // line is not, and nothing the holder does can catch it.
    override fun maySendWrite(now: Long, believedExpiry: Long) = believedExpiry - now >= marginMs
}

// ---- from Damage.kt ----
/** The writes that landed when the lease they were made under was no longer valid at the lease service. */
fun staleWrites(run: RunResult): List<Write> =
    run.writes.filter { !run.leases.getValue(it.leaseId).validAt(it.landedAt) }   // the service's view, at landing

/**
 * The stale writes that did real harm: each landed after the ledger had already applied a write under a newer lease,
 * so it overwrote what the newer holder wrote. Lease ids grow with every grant, so "newer" means a larger id.
 */
fun clobbers(run: RunResult): List<Write> {
    val out = mutableListOf<Write>()
    var newest = 0
    for (w in run.writes) {                      // in the order the ledger applied them
        if (w.leaseId < newest) out += w         // a newer holder has written already
        newest = maxOf(newest, w.leaseId)
    }
    return out
}

/**
 * Stale writes summed over [seeds], for each pause length in [pauseLengths]: one random run per seed, with pauses of
 * that length arriving at random on both holders.
 */
fun sweep(policy: HolderPolicy, pauseLengths: List<Long>, seeds: IntRange, base: Scenario = Scenario()): Map<Long, Int> =
    pauseLengths.associateWith { pause ->
        seeds.sumOf { seed -> staleWrites(simulate(base.copy(seed = seed, pauseMs = pause), policy)).size }
    }
