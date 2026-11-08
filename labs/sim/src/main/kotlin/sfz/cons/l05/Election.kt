package sfz.cons.l05

// Lesson cons-05 lab, part 2: leader election on the coordination service, and a ledger that fences
// stale leaders. Your job: Candidate.campaign(), Candidate.check() and Ledger.append(). The rest of
// Candidate (its lease loop, its work loop, pausing and crashing) is provided.

/** One write the ledger accepted. */
data class LedgerEntry(val token: Long, val writer: String, val at: Long)

/**
 * The resource the leader protects: the payout ledger. Every write carries the writer's fencing token.
 * A [fenced] ledger remembers the highest token it has accepted and refuses any lower one. An unfenced
 * ledger accepts everything, which is what you get when the resource trusts the lock.
 */
class Ledger(private val sim: Sim, val fenced: Boolean = true) {
    val entries = ArrayList<LedgerEntry>()
    var rejected = 0
        private set

    /** The highest token accepted so far; 0 before the first write. */
    var highestToken = 0L
        private set

    /**
     * Appends a write from [writer] carrying [token] and returns true, or refuses it and returns false.
     * Fenced: refuse a token lower than [highestToken] (count it in [rejected]); accept an equal or
     * higher one and remember it. The same leader writes many times with the same token, so equal is fine.
     */
    fun append(token: Long, writer: String): Boolean {
        if (!fenced) {
            entries += LedgerEntry(token, writer, sim.now)
            return true
        }
        TODO("cons-05: refuse tokens lower than the highest accepted")
    }
}

/**
 * A process that wants to lead, using the ZooKeeper election recipe (Curator's LeaderLatch works the
 * same way): create an ephemeral sequential node under [electionPath]; the lowest number leads; every
 * other candidate watches only the node just before its own, so a leader's death wakes one process,
 * not all of them. While it leads, its fencing token is its node's createRevision.
 */
class Candidate(
    val name: String,
    private val sim: Sim,
    private val coord: Coordinator,
    private val ledger: Ledger,
    val electionPath: String = "/election",
    val ttlMs: Long = 3_000,
    /** A leader writes to the ledger this often. */
    val workEveryMs: Long = 500,
) {
    var session = 0L
        private set

    /** The path of this candidate's own node, or null when it has none. */
    var node: String? = null
        private set

    var isLeader = false
        private set

    /** The fencing token this candidate writes with: its node's createRevision once it leads. */
    var token = 0L
        private set

    /** How many watches this candidate has set (a candidate that is not first should set one per check). */
    var watchesSet = 0
        private set

    var crashed = false
        private set

    private var pausedUntil = 0L

    // ---------------------------------------------------------------- your part

    /**
     * Joins the election: create an ephemeral, sequential node "$electionPath/n-" in [session], with
     * [name] as its data, remember its path in [node], then [check].
     */
    fun campaign() {
        TODO("cons-05: create your ephemeral sequential node, then check")
    }

    /**
     * Decides whether this candidate leads. Called after [campaign] and whenever a watch fires.
     *
     * - If [node] is null or no longer exists, this candidate is out: set [isLeader] false and return.
     * - List the children of [electionPath]. If this candidate's node is the first, it leads: set
     *   [isLeader] and set [token] to the node's createRevision.
     * - Otherwise it follows: set [isLeader] false, count one more in [watchesSet], and watch the node
     *   just before its own: `coord.watch(path) { onWatch() }`. [onWatch] calls [check] again.
     */
    fun check() {
        TODO("cons-05: lead if your node is first, else watch the node before yours")
    }

    // ---------------------------------------------------------------- provided

    /** Opens a session, keeps it alive every ttl/3, joins the election and starts working. */
    fun start() {
        session = coord.openSession(ttlMs)
        keepAliveLoop(session)
        campaign()
        workLoop()
    }

    private var pendingCheck = false

    /** A watch fired. A frozen process can't react until it wakes up, so then the check waits. */
    fun onWatch() {
        if (crashed) return
        if (sim.now < pausedUntil) pendingCheck = true else check()
    }

    private var loop = 0

    /** Renews every ttl/3. Starting a new loop retires the old one, so there is only ever one. */
    private fun keepAliveLoop(s: Long, id: Int = ++loop) {
        sim.after(ttlMs / 3) {
            if (crashed || id != loop) return@after
            if (sim.now < pausedUntil) return@after               // frozen: pause() restarts the loop on waking
            if (renew()) keepAliveLoop(s, id)
        }
    }

    /**
     * Renews the lease and returns true if it was still alive. If it had expired, this candidate learns
     * that it lost its node (and any leadership), opens a new session and rejoins at the back of the queue.
     */
    private fun renew(): Boolean {
        if (coord.keepAlive(session)) return true
        isLeader = false
        node = null
        session = coord.openSession(ttlMs)
        keepAliveLoop(session)
        campaign()
        return false
    }

    private fun workLoop() {
        sim.after(workEveryMs) {
            if (crashed) return@after
            if (sim.now >= pausedUntil && isLeader) write()
            workLoop()
        }
    }

    private fun write() {
        ledger.append(token, name)
    }

    /**
     * Freezes this process for [ms], as a long GC pause or a stopped VM does. A leader had already
     * decided to write when the pause hit: when it wakes, it writes first, with the token it had, and
     * only then renews its lease and finds out whether it still has one.
     */
    fun pause(ms: Long) {
        if (crashed || sim.now < pausedUntil) return              // already frozen
        val wasLeader = isLeader
        pausedUntil = sim.now + ms
        sim.at(pausedUntil) {
            if (crashed) return@at
            if (wasLeader && isLeader) write()                    // the write that was in flight when it froze
            if (renew()) keepAliveLoop(session)
            if (pendingCheck && node != null) {
                pendingCheck = false
                check()
            }
        }
    }

    /** Stops this process for good: no more lease renewals, so its session expires after the ttl. */
    fun crash() {
        crashed = true
        isLeader = false
    }
}
