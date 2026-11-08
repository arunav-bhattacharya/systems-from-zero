// Copies of the lab's given code and reference answers, so the demos run without your solution.
// Demos don't see src/main or src/solution.
package sfz.cons.l02.demo

import java.util.PriorityQueue
import kotlin.random.Random

/**
 * Lesson cons-02 (given): histories of a key-value store whose keys are registers with read, write
 * and compare-and-set. Each operation is a bar: the client sent the request at [Op.start] and got the
 * answer at [Op.end] (milliseconds).
 */
enum class Kind { READ, WRITE, CAS }

/**
 * One operation as its client saw it.
 * - READ: [value] is what the read returned (null: the key had never been written).
 * - WRITE: [value] is what it wrote.
 * - CAS: "if the key holds [expected], set it to [value]"; [ok] says whether it did.
 */
data class Op(
    val id: Int,
    val process: String,
    val key: String,
    val kind: Kind,
    val value: Int?,
    val start: Long,
    val end: Long,
    val expected: Int? = null,
    val ok: Boolean = true,
) {
    override fun toString(): String {
        val what = when (kind) {
            Kind.READ -> "r($key)=${value ?: "-"}"
            Kind.WRITE -> "w($key,$value)"
            Kind.CAS -> "cas($key,${expected ?: "-"}->$value)=${if (ok) "ok" else "fail"}"
        }
        return "$process:$what@$start-$end"
    }
}

/** A list of operations; [keys] and [ofKey] split it into one sub-history per key. */
class History(ops: List<Op>) {
    val ops: List<Op> = ops.sortedWith(compareBy({ it.start }, { it.id }))

    init {
        for (op in this.ops) require(op.start <= op.end) { "$op ends before it starts" }
    }

    val keys: List<String> get() = ops.map { it.key }.distinct()
    fun ofKey(key: String): List<Op> = ops.filter { it.key == key }
    override fun toString(): String = ops.joinToString("\n")
}

/** `history { "A".write("x", 1, 0..10); "B".read("x", 1, 5..20); "C".cas("x", 1, 2, true, 30..40) }` */
class HistoryBuilder {
    private val ops = mutableListOf<Op>()
    fun String.write(key: String, value: Int, at: IntRange) {
        ops += Op(ops.size, this, key, Kind.WRITE, value, at.first.toLong(), at.last.toLong())
    }
    fun String.read(key: String, value: Int?, at: IntRange) {
        ops += Op(ops.size, this, key, Kind.READ, value, at.first.toLong(), at.last.toLong())
    }
    fun String.cas(key: String, expected: Int?, value: Int, ok: Boolean, at: IntRange) {
        ops += Op(ops.size, this, key, Kind.CAS, value, at.first.toLong(), at.last.toLong(), expected, ok)
    }
    fun build() = History(ops)
}

fun history(block: HistoryBuilder.() -> Unit): History = HistoryBuilder().apply(block).build()

/**
 * The sequential specification of one register (given): what a single copy, doing one operation at
 * a time, would answer. [step] returns whether [op]'s recorded answer is possible from [state], and
 * the state afterwards. This is Porcupine's `Step(state, input, output) -> (ok, newState)`.
 */
object Register {
    fun step(state: Int?, op: Op): Pair<Boolean, Int?> = when (op.kind) {
        Kind.READ -> (op.value == state) to state
        Kind.WRITE -> true to op.value
        Kind.CAS -> if (state == op.expected) op.ok to (if (op.ok) op.value else state) else !op.ok to state
    }
}


/**
 * Virtual time for lesson cons-02 (given). Nothing sleeps: [run] takes the scheduled events in time
 * order and moves [now] from one to the next. All randomness comes from [random], seeded, so a seed
 * replays exactly the same run. Two events at the same millisecond run in the order they were added.
 */
class Sim(seed: Long) {
    val random = Random(seed)
    var now: Long = 0
        private set

    private class Event(val at: Long, val seq: Long, val action: () -> Unit)

    private var seq = 0L
    private val queue = PriorityQueue(compareBy<Event>({ it.at }, { it.seq }))

    fun after(delayMs: Long, action: () -> Unit) {
        queue += Event(now + delayMs, seq++, action)
    }

    /** Runs events until none are left or the clock passes [untilMs]. */
    fun run(untilMs: Long = Long.MAX_VALUE) {
        while (queue.isNotEmpty() && queue.peek().at <= untilMs) {
            val e = queue.poll()
            now = e.at
            e.action()
        }
    }
}

/**
 * A network that delivers every message, after a random delay. Most messages take [minMs] to [maxMs];
 * a fraction [slowChance] of them hit a slow path and take up to [slowMaxMs] (a long tail, as on real
 * networks). Messages can overtake each other. [sent] counts messages, for comparing protocols.
 */
class Network(
    private val sim: Sim,
    private val minMs: Long = 1,
    private val maxMs: Long = 10,
    private val slowChance: Double = 0.1,
    private val slowMaxMs: Long = 100,
) {
    var sent = 0L
        private set

    fun send(deliver: () -> Unit) {
        sent++
        val r = sim.random
        val delay = if (r.nextDouble() < slowChance) r.nextLong(maxMs, slowMaxMs + 1) else r.nextLong(minMs, maxMs + 1)
        sim.after(delay, deliver)
    }
}

/**
 * Lesson cons-02: two simulated replicated stores, and a workload that records what their clients
 * saw as a [History]. Everything runs on a [Sim], so one seed gives one exact history.
 */
interface Store {
    fun read(client: String, key: String, done: (Int?) -> Unit)
    fun write(client: String, key: String, value: Int, done: () -> Unit)
    /** Compare-and-set. Stores that can't do it atomically return false from [supportsCas]. */
    fun cas(client: String, key: String, expected: Int?, value: Int, done: (Boolean) -> Unit): Unit =
        error("this store has no compare-and-set")
    val supportsCas: Boolean get() = false
}

/**
 * Single-leader replication (given). The leader applies every write and CAS on arrival and answers.
 * It sends each change to one follower asynchronously. Reads go to the leader, or to the follower
 * when [followerReads] is true (the "read from a replica to offload the leader" setup).
 */
class SingleLeaderStore(private val net: Network, private val followerReads: Boolean = false) : Store {
    private val leader = mutableMapOf<String, Int?>()
    private val follower = mutableMapOf<String, Pair<Long, Int?>>()   // key -> (version, value)
    private var version = 0L

    private fun replicate(key: String) {
        val v = ++version
        val value = leader[key]
        net.send { if ((follower[key]?.first ?: 0) < v) follower[key] = v to value }   // keep the newest
    }

    override fun read(client: String, key: String, done: (Int?) -> Unit) = net.send {
        val value = if (followerReads) follower[key]?.second else leader[key]
        net.send { done(value) }
    }

    override fun write(client: String, key: String, value: Int, done: () -> Unit) = net.send {
        leader[key] = value
        replicate(key)
        net.send { done() }
    }

    override fun cas(client: String, key: String, expected: Int?, value: Int, done: (Boolean) -> Unit) = net.send {
        val ok = leader[key] == expected
        if (ok) {
            leader[key] = value
            replicate(key)
        }
        net.send { done(ok) }
    }

    override val supportsCas get() = true
}

/** A replica's copy of a key: the value and the tag that orders writes (higher version wins, then writer name). */
data class Tagged(val version: Int, val writer: String, val value: Int?) : Comparable<Tagged> {
    override fun compareTo(other: Tagged) = compareValuesBy(this, other, { it.version }, { it.writer })

    companion object {
        val NONE = Tagged(0, "", null)
    }
}

/**
 * Dynamo-style leaderless replication with [n] replicas, write quorum [w] and read quorum [r], and
 * w + r > n. A client talks to every replica itself.
 *
 * Write (given, the ABD protocol's write): ask all replicas for their tag, wait for [r] answers, pick
 * a version one higher than the highest seen, send the tagged value to all, wait for [w] acks. A
 * replica keeps a tagged value only if its tag is higher than what it has.
 *
 * Read: ask all replicas, wait for [r] answers, take the value with the highest tag, then
 * [finishRead]. When [syncReadRepair] is true, the read must not answer until that value is on a
 * write quorum. That is exercise 2.
 */
class QuorumStore(
    private val net: Network,
    private val n: Int = 3,
    private val w: Int = 2,
    private val r: Int = 2,
    private val syncReadRepair: Boolean = false,
) : Store {
    init {
        require(w + r > n) { "w + r must be more than n" }
    }

    private val replicas = List(n) { mutableMapOf<String, Tagged>() }

    /** Sends [tagged] to every replica and calls [then] once [w] of them have stored or already had something newer. */
    private fun writeToQuorum(key: String, tagged: Tagged, then: () -> Unit) {
        var acks = 0
        for (replica in replicas) net.send {
            if (tagged > (replica[key] ?: Tagged.NONE)) replica[key] = tagged
            net.send { if (++acks == w) then() }
        }
    }

    /** Asks every replica for its copy and calls [then] with the highest of the first [r] answers. */
    private fun queryQuorum(key: String, then: (Tagged) -> Unit) {
        val answers = mutableListOf<Tagged>()
        for (replica in replicas) net.send {
            val copy = replica[key] ?: Tagged.NONE
            net.send {
                answers += copy
                if (answers.size == r) then(answers.max())
            }
        }
    }

    override fun write(client: String, key: String, value: Int, done: () -> Unit) =
        queryQuorum(key) { highest -> writeToQuorum(key, Tagged(highest.version + 1, client, value), done) }

    override fun read(client: String, key: String, done: (Int?) -> Unit) =
        queryQuorum(key) { highest -> finishRead(key, highest, done) }

    /**
     * Exercise 2 (reference answer). Without repair the read answers at once. With [syncReadRepair]
     * it first makes sure a write quorum holds the value it is about to return, so any read that
     * starts after this one finishes will meet that value in at least one of its r replicas.
     */
    private fun finishRead(key: String, highest: Tagged, done: (Int?) -> Unit) {
        if (!syncReadRepair) return done(highest.value)
        writeToQuorum(key, highest) { done(highest.value) }   // the second round trip ABD pays for
    }
}

/**
 * A workload (given): [processes] clients, each running [opsEach] operations one after another with a
 * random pause of 0 to 10 ms between them, on [keys]. Writes write fresh values (1, 2, 3...). On a
 * store with CAS, a quarter of the operations are a CAS that expects the last value that client saw.
 * Returns what the clients saw.
 */
fun record(
    seed: Long,
    processes: Int = 3,
    opsEach: Int = 10,
    keys: List<String> = listOf("balance"),
    store: (Network) -> Store,
): History {
    val sim = Sim(seed)
    val net = Network(sim)
    val s = store(net)
    val ops = mutableListOf<Op>()
    var nextValue = 1
    for (p in 1..processes) {
        val name = "c$p"
        var lastSeen: Int? = null
        var left = opsEach
        fun next() {
            if (left-- == 0) return
            sim.after(sim.random.nextLong(0, 11)) {
                val key = keys[sim.random.nextInt(keys.size)]
                val start = sim.now
                val dice = sim.random.nextInt(4)
                when {
                    s.supportsCas && dice == 0 -> {
                        val v = nextValue++
                        val expected = lastSeen
                        s.cas(name, key, expected, v) { ok ->
                            ops += Op(ops.size, name, key, Kind.CAS, v, start, sim.now, expected, ok)
                            if (ok) lastSeen = v
                            next()
                        }
                    }
                    dice == 1 -> {
                        val v = nextValue++
                        s.write(name, key, v) {
                            ops += Op(ops.size, name, key, Kind.WRITE, v, start, sim.now)
                            lastSeen = v
                            next()
                        }
                    }
                    else -> s.read(name, key) { v ->
                        ops += Op(ops.size, name, key, Kind.READ, v, start, sim.now)
                        lastSeen = v
                        next()
                    }
                }
            }
        }
        next()
    }
    sim.run()
    return History(ops)
}
