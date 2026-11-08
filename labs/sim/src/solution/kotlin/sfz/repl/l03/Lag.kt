package sfz.repl.l03

/**
 * Lesson repl-03: reading from followers that lag. One leader's log, followers that apply it
 * [Replica.lagMs] behind, and sessions that carry a log position so their reads never go below it.
 *
 * Time is a number the tests pass in (milliseconds), so every lag and every anomaly is exact. A
 * follower's position at a moment is a pure function of the log and its lag: nothing runs in the
 * background.
 */

/** One committed write: its log position (1, 2, 3...), commit time, key and value. */
data class Entry(val position: Long, val committedAt: Long, val key: String, val value: String)

/** Something a read can be served by: the leader or a follower. */
interface Node {
    val name: String

    /** The log position this node has applied at time [now]. */
    fun position(now: Long): Long

    /** The value of [key] as of [position], or null if no entry up to there wrote it. */
    fun valueAt(key: String, position: Long): String?

    /** Every entry up to [position], in log order. */
    fun entriesUpTo(position: Long): List<Entry>
}

/** The leader (given): it appends every write to its log and answers with the new position. */
class Leader(override val name: String = "leader") : Node {
    val log: MutableList<Entry> = mutableListOf()

    /** Commits [key] = [value] at [now] and returns its position: the LSN the client hears back. */
    fun write(now: Long, key: String, value: String): Long {
        val entry = Entry(log.size + 1L, now, key, value)
        log += entry
        return entry.position
    }

    override fun position(now: Long): Long = log.count { it.committedAt <= now }.toLong()

    override fun valueAt(key: String, position: Long): String? =
        log.asSequence().take(position.toInt()).lastOrNull { it.key == key }?.value

    override fun entriesUpTo(position: Long): List<Entry> = log.take(position.toInt())
}

/**
 * A follower (given). It applies each entry [lagMs] after the leader committed it. [pause] freezes
 * its position, as pg_wal_replay_pause() does; [resume] lets it catch up at once. A follower that
 * has died ([alive] false) serves nothing.
 */
class Replica(override val name: String, var lagMs: Long, private val leader: Leader) : Node {
    var alive: Boolean = true
    private var frozenAt: Long? = null

    fun pause(now: Long) {
        frozenAt = position(now)
    }

    fun resume() {
        frozenAt = null
    }

    override fun position(now: Long): Long =
        frozenAt ?: leader.log.count { it.committedAt + lagMs <= now }.toLong()

    /** When this follower will have applied [position], or null if it is paused below it. */
    fun reaches(position: Long): Long? {
        if (position == 0L) return 0
        frozenAt?.let { if (it < position) return null }
        return leader.log[position.toInt() - 1].committedAt + lagMs
    }

    override fun valueAt(key: String, position: Long): String? = leader.valueAt(key, position)
    override fun entriesUpTo(position: Long): List<Entry> = leader.entriesUpTo(position)
}

/** What a client remembers between requests: the session token. */
class Session(val user: String) {
    /** The position of this session's own last write. 0 if it has not written. */
    var lastWritten: Long = 0

    /** The highest position any of this session's reads was served at. */
    var lastSeen: Long = 0
}

/** Where a read goes, and how long it waits there first. */
data class Route(val node: Node, val waitMs: Long = 0)

/** What a read returned: who served it, at which position, after how long a wait. */
data class Read(val node: String, val position: Long, val value: String?, val waitMs: Long)

/** The client side (given): writes go to the leader, reads go wherever a [Route] says. */
class Client(val leader: Leader) {
    fun write(session: Session, now: Long, key: String, value: String) {
        session.lastWritten = maxOf(session.lastWritten, leader.write(now, key, value))
    }

    fun read(session: Session, now: Long, key: String, route: Route): Read {
        val at = now + route.waitMs
        val position = route.node.position(at)
        session.lastSeen = maxOf(session.lastSeen, position)
        return Read(route.node.name, position, route.node.valueAt(key, position), route.waitMs)
    }
}

/**
 * Sticky routing (given): each user always reads from the same live follower, chosen by a hash of
 * the user. Live followers are numbered in list order; a dead one drops out of the numbering.
 */
fun stickyReplica(user: String, replicas: List<Replica>): Replica? {
    val live = replicas.filter { it.alive }
    if (live.isEmpty()) return null
    return live[Math.floorMod(user.hashCode(), live.size)]
}

/**
 * Exercise 1 of 3: read-your-writes, with a bounded wait.
 *
 * The load balancer offered [replica] for this read at time [now]. If it has already applied the
 * session's last write (its position at [now] is at least session.lastWritten), read there with no
 * wait. If it will get there within [maxWaitMs] (see [Replica.reaches]), read there after waiting
 * just long enough. Otherwise read from [leader] with no wait. A dead replica is never used.
 *
 * This is the "remember the LSN of your last commit" recipe: on PostgreSQL the client keeps
 * pg_current_wal_lsn() from its commit and compares it with pg_last_wal_replay_lsn() on the standby.
 */
fun readYourWrites(session: Session, replica: Replica, leader: Leader, now: Long, maxWaitMs: Long = 0): Route {
    if (!replica.alive) return Route(leader)
    if (replica.position(now) >= session.lastWritten) return Route(replica)            // already there
    val readyAt = replica.reaches(session.lastWritten) ?: return Route(leader)          // paused below it
    val wait = readyAt - now
    return if (wait <= maxWaitMs) Route(replica, wait) else Route(leader)                // wait, or give up
}

/**
 * Exercise 2 of 3: monotonic reads (and read-your-writes) without waiting.
 *
 * The session must never be served below the larger of session.lastSeen and session.lastWritten.
 * Try the session's sticky follower first ([stickyReplica]), then every other live follower in list
 * order, and return the first one whose position at [now] is at least that token. If none is, read
 * from [leader].
 */
fun monotonicReads(session: Session, replicas: List<Replica>, leader: Leader, now: Long): Route {
    val token = maxOf(session.lastSeen, session.lastWritten)
    val sticky = stickyReplica(session.user, replicas)
    val order = listOfNotNull(sticky) + replicas.filter { it.alive && it !== sticky }
    return order.firstOrNull { it.position(now) >= token }?.let { Route(it) } ?: Route(leader)
}

/** A payment event. Events of one payment depend on each other: a capture follows its authorization. */
data class PaymentEvent(val paymentId: String, val type: String)

/**
 * Exercise 3 of 3: which shard's log an event goes to, so that every observer sees the events of a
 * payment in the order they happened.
 *
 * Return a shard number in 0 until [shards] that depends only on the event's paymentId (use
 * Math.floorMod on its hashCode). Then all events of one payment land in one log, and a follower of
 * that log shows them as a prefix: never a capture without its authorization.
 */
fun shardFor(event: PaymentEvent, shards: Int): Int = Math.floorMod(event.paymentId.hashCode(), shards)

/**
 * The obvious-looking alternative (given): a shard per kind of event, authorizations on shard 0 and
 * captures and refunds on shard 1. Each log is in order, but the two logs replicate separately.
 */
fun shardByType(event: PaymentEvent, shards: Int): Int = (if (event.type == "authorized") 0 else 1) % shards
