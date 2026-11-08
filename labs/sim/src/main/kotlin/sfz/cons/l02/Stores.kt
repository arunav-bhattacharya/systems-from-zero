package sfz.cons.l02

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
     * Exercise 2. As given, the read answers at once with the newest value it saw. A later read can
     * then reach two replicas the write hasn't reached yet and return the older value, which is not
     * linearizable. Fix it: when [syncReadRepair] is true, first put [highest] on a write quorum with
     * [writeToQuorum], and answer only when that is done. Leave the false case as it is.
     */
    private fun finishRead(key: String, highest: Tagged, done: (Int?) -> Unit) {
        done(highest.value)
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
