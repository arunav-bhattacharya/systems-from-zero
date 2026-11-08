package sfz.cons.l05

import java.util.TreeMap

// Lesson cons-05 lab, part 1: a small coordination service on virtual time.
// It models what ZooKeeper and etcd give you, minus the consensus underneath (lesson 4 built that):
// one counter that every change bumps (the revision), nodes that belong to a session (ephemeral),
// names with a counter in them (sequential), sessions kept alive by a lease, and one-shot watches.
// Your job: create() and expire(). Everything else in this file is provided.

/** One node (a znode in ZooKeeper, a key in etcd). */
data class Node(
    val path: String,
    val data: String,
    /** The revision of the change that created this node: etcd's create_revision, ZooKeeper's cZxid. */
    val createRevision: Long,
    /** The session that owns this node if it is ephemeral, or null if it stays until someone deletes it. */
    val session: Long?,
)

enum class EventType { CREATED, DELETED }

/** What a watch delivers: what happened to which path, and the revision of that change. */
data class WatchEvent(val type: EventType, val path: String, val revision: Long)

class Coordinator(
    private val sim: Sim,
    /** Watch events reach the client this long after the change: notifications are never instant. */
    private val watchDelayMs: Long = 2,
) {
    /** The revision of the latest change. Every create and every delete adds exactly one. */
    var revision = 0L
        private set

    /** How many watch events this service has delivered, to count herd effects. */
    var notificationsSent = 0
        private set

    private class Session(val id: Long, val ttlMs: Long, var expiresAt: Long, var expired: Boolean = false)

    private val nodes = TreeMap<String, Node>()
    private val sessions = HashMap<Long, Session>()
    private val sequences = HashMap<String, Long>()
    private val watches = HashMap<String, MutableList<(WatchEvent) -> Unit>>()
    private var nextSession = 1L

    // ---------------------------------------------------------------- your part

    /**
     * Creates a node and returns it, or returns null if [path] (after sequential naming) already exists.
     *
     * - With [sequential], append the parent's next sequence number to [path], ten digits, zero-padded,
     *   starting at 0: creating "/election/n-" three times gives "/election/n-0000000000", then
     *   "...0000000001", then "...0000000002". The parent is everything before the last '/'. Use
     *   [nextSequence]; a number is never reused, even after its node is deleted.
     * - With a [session], the node is ephemeral: it belongs to that session. Creating a node in a
     *   session that has expired (or never existed) throws [IllegalStateException]: use [isAlive].
     * - A successful create is one change: bump [revision] and store it as the node's createRevision.
     * - Call [fire] with CREATED so a watch set on a path that didn't exist yet hears about it.
     */
    fun create(path: String, data: String, session: Long? = null, sequential: Boolean = false): Node? {
        TODO("cons-05: create a node, with sequential naming, an owning session and a new revision")
    }

    /**
     * Ends a session whose lease ran out: mark it expired, then delete every ephemeral node it owns, in
     * path order, with [delete], so each deletion is its own revision and fires its own watches. The
     * service calls this itself when a lease ends (see [openSession]); the client is never asked.
     */
    fun expire(sessionId: Long) {
        TODO("cons-05: mark the session expired and delete its ephemeral nodes")
    }

    // ---------------------------------------------------------------- provided

    /**
     * Opens a session whose lease lasts [ttlMs] and returns its id. The client must call [keepAlive]
     * before the lease ends; the service checks at the expiry time and calls [expire] if it didn't.
     */
    fun openSession(ttlMs: Long): Long {
        val s = Session(nextSession++, ttlMs, sim.now + ttlMs)
        sessions[s.id] = s
        scheduleCheck(s)
        return s.id
    }

    private fun scheduleCheck(s: Session) {
        sim.at(s.expiresAt) {
            if (s.expired) return@at
            if (sim.now >= s.expiresAt) expire(s.id) else scheduleCheck(s)   // renewed in the meantime: look again later
        }
    }

    /** Renews the lease for another ttl. Returns false if the session has already expired. */
    fun keepAlive(sessionId: Long): Boolean {
        val s = sessions[sessionId] ?: return false
        if (s.expired) return false
        s.expiresAt = sim.now + s.ttlMs
        return true
    }

    /** Closes a session on purpose (a clean shutdown): its ephemeral nodes go at once. */
    fun close(sessionId: Long) = expire(sessionId)

    fun isAlive(sessionId: Long): Boolean = sessions[sessionId]?.let { !it.expired } ?: false

    fun get(path: String): Node? = nodes[path]

    /** The direct children of [parent], sorted by name (so sequential nodes come in sequence order). */
    fun children(parent: String): List<Node> =
        nodes.subMap("$parent/", "$parent/￿").values.filter { '/' !in it.path.substring(parent.length + 1) }

    /** Deletes [path]. Returns false if it didn't exist. One change: bumps [revision] and fires watches. */
    fun delete(path: String): Boolean {
        nodes.remove(path) ?: return false
        revision++
        fire(EventType.DELETED, path)
        return true
    }

    /**
     * Sets a one-shot watch on [path]: [onEvent] runs once, [watchDelayMs] after the next create or
     * delete of that path, and then the watch is gone (set a new one to keep watching).
     */
    fun watch(path: String, onEvent: (WatchEvent) -> Unit) {
        watches.getOrPut(path) { ArrayList() } += onEvent
    }

    /** Delivers and removes every watch on [path], each [watchDelayMs] from now. */
    fun fire(type: EventType, path: String) {
        val waiting = watches.remove(path) ?: return
        val event = WatchEvent(type, path, revision)
        for (w in waiting) {
            notificationsSent++
            sim.after(watchDelayMs) { w(event) }
        }
    }

    /** The next sequence number under [parent]: 0, 1, 2, ... per parent, never reused. */
    fun nextSequence(parent: String): Long {
        val n = sequences[parent] ?: 0L
        sequences[parent] = n + 1
        return n
    }

    fun parentOf(path: String): String = path.substringBeforeLast('/')
}
