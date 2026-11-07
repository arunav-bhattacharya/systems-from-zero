package sfz.internals.l07

/** What the commit log (PostgreSQL's pg_xact) knows about a transaction id. */
enum class TxStatus { ACTIVE, COMMITTED, ABORTED }

/** When a transaction takes its snapshot: once at the start, or again for every statement. */
enum class Isolation { READ_COMMITTED, REPEATABLE_READ }

/**
 * One version of a row: a balance in cents, stamped with the transaction that created it ([xmin]) and the
 * one that deleted or replaced it ([xmax], 0 while nobody has). PostgreSQL keeps the same two numbers in
 * every tuple header as `t_xmin` and `t_xmax`.
 */
class Version(val value: Long, val xmin: Long) {
    var xmax: Long = 0
    override fun toString() = "($value, xmin=$xmin, xmax=$xmax)"
}

/**
 * Which transactions' changes a reader can see, in the shape `pg_current_snapshot()` prints as
 * `xmin:xmax:active`:
 * - every id below [xmin] had already finished (committed or aborted) when the snapshot was taken,
 * - no id from [xmax] up had finished (in this store, none of them had even started),
 * - [active] holds the ids in between that were still running, apart from [owner] itself.
 */
data class Snapshot(val owner: Long, val xmin: Long, val xmax: Long, val active: Set<Long>)

/** Thrown when a write would overwrite a change the writer cannot see. The transaction must abort and retry. */
class WriteConflict(message: String) : RuntimeException(message)

/** A transaction: its id, its isolation level and the snapshot its last statement used. */
class Tx(val id: Long, val isolation: Isolation) {
    /** Set by [MvccStore]: the snapshot of the transaction (repeatable read) or of its last statement (read committed). */
    lateinit var snapshot: Snapshot
}

/**
 * A tiny multi-version store of account balances, with PostgreSQL's design: every write appends a new
 * [Version] to the key's chain (oldest first) and stamps the old one with the writer's id as its `xmax`.
 * Nothing is overwritten in place. A reader picks the one version its [Snapshot] can see. [vacuum] later
 * removes the versions no snapshot can see any more.
 *
 * Your job: write [sees], [isVisible], [get], [checkWritable], [put], [delete] and [vacuum].
 * Transactions, snapshots, the commit log and [horizon] are done: everything below the "provided" line.
 */
class MvccStore {
    private val chains = HashMap<String, MutableList<Version>>()   // key -> versions, oldest first
    private val clog = HashMap<Long, TxStatus>()                   // the commit log: id -> status
    private val running = LinkedHashMap<Long, Tx>()                // transactions that have not ended
    private var nextXid = FIRST_XID

    /**
     * Are the changes of transaction [xid] visible in [snapshot]? Your own changes are. A transaction that
     * had not started, or was still running, when the snapshot was taken is not, even if it has committed
     * since. Any other transaction is visible exactly when the commit log says it committed.
     */
    fun sees(snapshot: Snapshot, xid: Long): Boolean {
        if (xid == snapshot.owner) return true                 // my own writes
        if (xid >= snapshot.xmax) return false                 // started after my snapshot
        if (xid in snapshot.active) return false               // was running when I took my snapshot
        return status(xid) == TxStatus.COMMITTED               // had finished: visible only if it committed
    }

    /** The visibility rule: the creator of [v] is visible to [snapshot], and its deleter (if any) is not. */
    fun isVisible(v: Version, snapshot: Snapshot): Boolean =
        sees(snapshot, v.xmin) && !(v.xmax != 0L && sees(snapshot, v.xmax))

    /** The balance of [key] as [tx] sees it, or null if no version is visible. */
    fun get(tx: Tx, key: String): Long? {
        val s = statementSnapshot(tx)
        // at most one version of a key is visible to a snapshot; the newest is the likely one
        return chains[key]?.lastOrNull { isVisible(it, s) }?.value
    }

    /**
     * Fails with [WriteConflict] if another transaction that [tx] cannot see created or deleted a version in
     * [chain] and has not aborted: it is still running, or it committed after [snapshot] was taken.
     */
    private fun checkWritable(tx: Tx, snapshot: Snapshot, chain: List<Version>) {
        for (v in chain) for (x in longArrayOf(v.xmin, v.xmax)) {
            if (x == 0L || x == tx.id) continue
            if (status(x) == TxStatus.ABORTED) continue        // an aborted write doesn't count
            if (!sees(snapshot, x)) {                          // running now, or committed after my snapshot
                throw WriteConflict("tx ${tx.id}: tx $x changed this row and tx ${tx.id} cannot see that change")
            }
        }
    }

    /**
     * Inserts or updates [key] in [tx]: the version [tx] sees (if any) gets `xmax = tx.id`, and a new version
     * with `xmin = tx.id` is appended. Checks [checkWritable] first.
     */
    fun put(tx: Tx, key: String, value: Long) {
        val s = statementSnapshot(tx)
        val chain = chains.getOrPut(key) { mutableListOf() }
        checkWritable(tx, s, chain)
        chain.lastOrNull { isVisible(it, s) }?.xmax = tx.id    // the old version ends here, but stays
        chain += Version(value, tx.id)                         // the new version starts here
    }

    /** Deletes [key] in [tx]: only sets `xmax` on the version [tx] sees. Returns false if there was none. */
    fun delete(tx: Tx, key: String): Boolean {
        val s = statementSnapshot(tx)
        val chain = chains[key] ?: return false
        checkWritable(tx, s, chain)
        val v = chain.lastOrNull { isVisible(it, s) } ?: return false
        v.xmax = tx.id                                         // a delete writes no new version
        return true
    }

    /**
     * Removes every version that no running or future snapshot can see: one created by an aborted
     * transaction, or one deleted by a committed transaction older than [horizon]. Returns how many it
     * removed. Keys left with no versions disappear.
     */
    fun vacuum(): Int {
        val h = horizon()
        fun dead(v: Version) = status(v.xmin) == TxStatus.ABORTED ||
            (v.xmax != 0L && v.xmax < h && status(v.xmax) == TxStatus.COMMITTED)
        var removed = 0
        for (chain in chains.values) {
            val before = chain.size
            chain.removeAll { dead(it) }
            removed += before - chain.size
        }
        chains.values.removeAll { it.isEmpty() }
        return removed
    }

    // ---------------------------------------------------------------- provided

    /** Starts a transaction with the next id and, for repeatable read, takes its snapshot now. */
    fun begin(isolation: Isolation = Isolation.REPEATABLE_READ): Tx {
        val tx = Tx(nextXid++, isolation)
        clog[tx.id] = TxStatus.ACTIVE
        running[tx.id] = tx
        tx.snapshot = takeSnapshot(tx.id)
        return tx
    }

    /** Commits [tx]: one entry in the commit log. Its versions don't change; readers now see them. */
    fun commit(tx: Tx) = end(tx, TxStatus.COMMITTED)

    /** Aborts [tx]. Its versions stay in the chains; they are invisible because the commit log says ABORTED. */
    fun abort(tx: Tx) = end(tx, TxStatus.ABORTED)

    /** The commit log's entry for [xid]. */
    fun status(xid: Long): TxStatus = clog[xid] ?: error("unknown transaction id $xid")

    /**
     * The oldest `xmin` of any running transaction's snapshot, or the next id if nothing is running.
     * Every transaction below it had finished before any snapshot still in use was taken.
     */
    fun horizon(): Long = running.values.minOfOrNull { it.snapshot.xmin } ?: nextXid

    /** Every version of [key], oldest first, visible or not (what pageinspect's heap_page_items shows). */
    fun versions(key: String): List<Version> = chains[key].orEmpty().toList()

    /** The number of versions in the whole store. */
    fun versionCount(): Int = chains.values.sumOf { it.size }

    /** The snapshot a statement of [tx] uses: a fresh one for read committed, the first one for repeatable read. */
    private fun statementSnapshot(tx: Tx): Snapshot {
        check(status(tx.id) == TxStatus.ACTIVE) { "tx ${tx.id} has already ended" }
        if (tx.isolation == Isolation.READ_COMMITTED) tx.snapshot = takeSnapshot(tx.id)
        return tx.snapshot
    }

    private fun takeSnapshot(owner: Long): Snapshot =
        Snapshot(owner, xmin = running.keys.min(), xmax = nextXid, active = running.keys - owner)

    private fun end(tx: Tx, status: TxStatus) {
        check(status(tx.id) == TxStatus.ACTIVE) { "tx ${tx.id} has already ended" }
        clog[tx.id] = status
        running.remove(tx.id)
    }

    companion object {
        /** The first transaction id handed out; small numbers below it are reserved, as in PostgreSQL. */
        const val FIRST_XID = 100L
    }
}
