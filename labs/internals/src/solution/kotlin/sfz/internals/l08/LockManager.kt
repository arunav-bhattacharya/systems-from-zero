package sfz.internals.l08

/** Shared (S) lets other readers in. Exclusive (X) lets nobody else in. */
enum class LockMode { SHARED, EXCLUSIVE }

/** One transaction's request for a lock on one resource: either granted, or waiting in the queue. */
class Request(val tx: Long, var mode: LockMode, var granted: Boolean) {
    override fun toString() = "T$tx:${if (mode == LockMode.SHARED) "S" else "X"}${if (granted) "" else "(waiting)"}"
}

/**
 * A lock manager for row locks, held until the transaction ends (strict two-phase locking).
 *
 * It never blocks a thread. [acquire] answers at once: true if the lock is granted, false if the transaction
 * must wait. Its request then sits in the resource's queue until a [release] grants it. That keeps every
 * test deterministic: the test plays the scheduler, as you do in the lesson's simulator.
 *
 * Each resource ("acct-1", a row) has one queue: granted requests first, then waiting requests in arrival
 * order. The rules you build:
 * - S is compatible with S. X is compatible with nothing.
 * - A new request is granted only if it is compatible with every granted request AND nobody is waiting
 *   ahead of it. That second rule keeps the queue fair: a stream of readers can't starve a writer.
 * - Asking for a lock you already hold in the same or a stronger mode is granted at once.
 * - Upgrading S to X: granted at once if you are the only holder; otherwise the upgrade waits at the head
 *   of the queue, ahead of the other waiters, until the other holders release.
 * - A transaction waits for at most one lock at a time.
 * - [release] (at commit or abort) drops all of a transaction's requests, granted or waiting, then grants
 *   waiting requests from the head of each queue, in order, until one can't be granted.
 *
 * Deadlocks: [waitsFor] builds the waits-for graph, [findCycle] finds a cycle in it, and
 * [detectDeadlocks] aborts victims until no cycle is left.
 *
 * Your job: write [acquire], [release], [waitsFor], [findCycle] and [detectDeadlocks]. Everything below the
 * "provided" line is done, including [grantWaiters], which [release] should call.
 */
class LockManager {
    private val queues = LinkedHashMap<String, MutableList<Request>>()   // resource -> requests
    private val aborted = LinkedHashSet<Long>()

    /**
     * Asks for [resource] in [mode] for [tx]. Returns true if [tx] now holds it, false if [tx] must wait.
     * Throws [IllegalStateException] if [tx] is already waiting for something.
     */
    fun acquire(tx: Long, resource: String, mode: LockMode): Boolean {
        check(waitingFor(tx) == null) { "T$tx is already waiting for ${waitingFor(tx)}" }
        check(tx !in aborted) { "T$tx was aborted" }
        val q = queues.getOrPut(resource) { mutableListOf() }
        val mine = q.find { it.tx == tx && it.granted }
        if (mine != null) {
            if (mine.mode == LockMode.EXCLUSIVE || mode == LockMode.SHARED) return true   // already strong enough
            if (q.none { it.granted && it.tx != tx }) {                                    // the only holder
                mine.mode = LockMode.EXCLUSIVE
                return true
            }
            // the upgrade waits for the other holders, ahead of everyone already waiting
            q.add(q.count { it.granted }, Request(tx, LockMode.EXCLUSIVE, granted = false))
            return false
        }
        // granted only if nobody waits ahead (fairness) and every holder is compatible
        val grant = q.all { it.granted && compatible(it.mode, mode) }
        q += Request(tx, mode, granted = grant)
        return grant
    }

    /**
     * Ends [tx]'s part in every queue: drops its granted and waiting requests, then grants what can now be
     * granted ([grantWaiters]). Returns the transactions that got a lock, in the order they got it.
     */
    fun release(tx: Long): List<Long> {
        val woken = mutableListOf<Long>()
        for (q in queues.values) {
            if (q.removeAll { it.tx == tx }) woken += grantWaiters(q)
        }
        queues.values.removeAll { it.isEmpty() }
        return woken
    }

    /**
     * The waits-for graph: an edge from every waiting transaction to every OTHER transaction ahead of it in
     * the same queue, granted or waiting, whose mode conflicts with what it asks for.
     */
    fun waitsFor(): Map<Long, Set<Long>> {
        val g = LinkedHashMap<Long, MutableSet<Long>>()
        for (q in queues.values) {
            for ((i, w) in q.withIndex()) {
                if (w.granted) continue
                for (ahead in q.subList(0, i)) {                         // holders, then earlier waiters
                    if (ahead.tx != w.tx && !compatible(ahead.mode, w.mode)) {
                        g.getOrPut(w.tx) { sortedSetOf() } += ahead.tx
                    }
                }
            }
        }
        return g
    }

    /**
     * A cycle in [waitsFor], as the transactions on it in edge order (each waits for the next, the last for
     * the first), or null if there is none. Search from the lowest transaction id, and follow edges in
     * increasing id order, so the answer is deterministic.
     */
    fun findCycle(): List<Long>? {
        val g = waitsFor()
        val done = HashSet<Long>()
        val path = ArrayList<Long>()                                     // the depth-first path we are on

        fun visit(t: Long): List<Long>? {
            path += t
            for (next in g[t].orEmpty().sorted()) {
                val at = path.indexOf(next)
                if (at >= 0) return path.subList(at, path.size).toList() // an edge back onto the path: a cycle
                if (next !in done) visit(next)?.let { return it }
            }
            path.removeAt(path.size - 1)
            done += t                                                    // no cycle through t
            return null
        }

        for (t in g.keys.sorted()) if (t !in done) visit(t)?.let { return it }
        return null
    }

    /**
     * Breaks every deadlock: while [findCycle] finds a cycle, abort its youngest transaction (the highest
     * id: it started last, so it has probably done the least work). Returns the victims in order.
     */
    fun detectDeadlocks(): List<Long> {
        val victims = mutableListOf<Long>()
        while (true) {
            val cycle = findCycle() ?: return victims
            val victim = cycle.max()
            abort(victim)                                                // releases its locks: others move on
            victims += victim
        }
    }

    // ---------------------------------------------------------------- provided

    /** Can a lock in mode [held] and one in mode [wanted] be held by two transactions at once? */
    fun compatible(held: LockMode, wanted: LockMode): Boolean =
        held == LockMode.SHARED && wanted == LockMode.SHARED

    /** Who holds [resource], and in which mode. */
    fun holders(resource: String): Map<Long, LockMode> =
        queues[resource].orEmpty().filter { it.granted }.associate { it.tx to it.mode }

    /** The transactions waiting for [resource], in queue order. */
    fun waiters(resource: String): List<Long> = queues[resource].orEmpty().filter { !it.granted }.map { it.tx }

    /** The resource [tx] is waiting for, or null. */
    fun waitingFor(tx: Long): String? = queues.entries.firstOrNull { (_, q) -> q.any { it.tx == tx && !it.granted } }?.key

    /** Aborts [tx]: it releases everything and may not ask for locks again. */
    fun abort(tx: Long): List<Long> {
        aborted += tx
        return release(tx)
    }

    fun wasAborted(tx: Long): Boolean = tx in aborted

    /**
     * Grants waiting requests from the head of [q], in order, while each is compatible with every granted
     * request of another transaction. Stops at the first one that isn't (first come, first served). An
     * upgrade turns the transaction's existing S request into X. Returns the transactions granted.
     */
    private fun grantWaiters(q: MutableList<Request>): List<Long> {
        val woken = mutableListOf<Long>()
        while (true) {
            val w = q.firstOrNull { !it.granted } ?: break
            if (q.any { it.granted && it.tx != w.tx && !compatible(it.mode, w.mode) }) break
            val held = q.find { it.granted && it.tx == w.tx }
            if (held != null) {                                          // an upgrade: S becomes X
                held.mode = w.mode
                q.remove(w)
            } else {
                w.granted = true
            }
            woken += w.tx
        }
        return woken
    }
}
