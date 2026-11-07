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
        TODO("check tx isn't waiting; already holding a strong enough lock: true; S->X upgrade: at once if sole holder, else queue it right after the granted requests; otherwise grant only if every request in the queue is granted and compatible")
    }

    /**
     * Ends [tx]'s part in every queue: drops its granted and waiting requests, then grants what can now be
     * granted ([grantWaiters]). Returns the transactions that got a lock, in the order they got it.
     */
    fun release(tx: Long): List<Long> {
        TODO("remove every request of tx from every queue; call grantWaiters on each queue you changed and collect who was woken; drop empty queues")
    }

    /**
     * The waits-for graph: an edge from every waiting transaction to every OTHER transaction ahead of it in
     * the same queue, granted or waiting, whose mode conflicts with what it asks for.
     */
    fun waitsFor(): Map<Long, Set<Long>> {
        TODO("for each waiting request, add an edge to every other transaction ahead of it in its queue whose mode conflicts")
    }

    /**
     * A cycle in [waitsFor], as the transactions on it in edge order (each waits for the next, the last for
     * the first), or null if there is none. Search from the lowest transaction id, and follow edges in
     * increasing id order, so the answer is deterministic.
     */
    fun findCycle(): List<Long>? {
        TODO("depth-first search over waitsFor() from the lowest id, children in increasing order; an edge back onto the current path is a cycle: return that part of the path")
    }

    /**
     * Breaks every deadlock: while [findCycle] finds a cycle, abort its youngest transaction (the highest
     * id: it started last, so it has probably done the least work). Returns the victims in order.
     */
    fun detectDeadlocks(): List<Long> {
        TODO("while findCycle() finds a cycle: abort its highest id and remember it; return the victims")
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
