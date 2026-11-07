package sfz.os.l05

/**
 * What one thread holds and waits for, read from its section of a `jstack -l` dump.
 *
 * @property holds the lock addresses this thread owns: `- locked <0x...>` lines (monitors, from
 *   `synchronized`) and the `- <0x...>` lines under "Locked ownable synchronizers:" (ReentrantLock and friends)
 * @property waitingFor the lock address this thread is blocked trying to get, or null. That is
 *   `- waiting to lock <0x...>` (synchronized) or `- parking to wait for  <0x...>` (ReentrantLock).
 *   `- waiting on <0x...>` is NOT a lock wait: a thread in `Object.wait()` has given its monitor back.
 */
data class ThreadLocks(val thread: String, val holds: List<String>, val waitingFor: String?)

object LockDump {
    /** A thread header: `"refund" #25 [62] prio=5 ... nid=62 waiting for monitor entry`. Group 1: the name. */
    val HEADER = Regex("""^"([^"]+)"\s.*\bnid=""")

    /** `- locked <0x000000008bb18d30> (a ...Account)`: a monitor the thread holds. Group 1: the address. */
    val LOCKED = Regex("""^\s+- locked <(0x[0-9a-f]+)>""")

    /** `- <0x000000008bb16ff0> (a ...ReentrantLock$NonfairSync)` under "Locked ownable synchronizers:". */
    val OWNABLE = Regex("""^\s+- <(0x[0-9a-f]+)>""")

    /** `- waiting to lock <0x...>` or `- parking to wait for  <0x...>`. Group 1: the address. */
    val WAITING = Regex("""^\s+- (?:waiting to lock|parking to wait for)\s+<(0x[0-9a-f]+)>""")

    /**
     * One [ThreadLocks] per thread header, in dump order. A thread's section is its header plus every
     * following line that is blank or starts with whitespace; it ends at the first line that starts with
     * anything else (the next header, "JNI global refs", the deadlock summary at the end).
     */
    fun parse(text: String): List<ThreadLocks> {
        val lines = text.lines()
        val result = mutableListOf<ThreadLocks>()
        for ((i, line) in lines.withIndex()) {
            val name = HEADER.find(line)?.groupValues?.get(1) ?: continue
            val body = lines.drop(i + 1).takeWhile { it.isEmpty() || it[0].isWhitespace() }   // stop at the next unindented line
            val holds = body.mapNotNull { (LOCKED.find(it) ?: OWNABLE.find(it))?.groupValues?.get(1) }
            val waiting = body.firstNotNullOfOrNull { WAITING.find(it)?.groupValues?.get(1) }
            result += ThreadLocks(name, holds, waiting)
        }
        return result
    }
}

/** Who waits for whom. An edge A -> B means A is blocked on a lock that B holds. */
class WaitForGraph(private val threads: List<ThreadLocks>) {

    /** waiter -> owner of the lock it waits for. A thread waiting for a lock nobody holds has no edge. */
    fun edges(): Map<String, String> {
        val owner = threads.flatMap { t -> t.holds.map { it to t.thread } }.toMap()     // lock address -> holder
        return threads.mapNotNull { t ->
            val holder = t.waitingFor?.let { owner[it] }
            if (holder == null || holder == t.thread) null else t.thread to holder
        }.toMap()
    }

    /**
     * One cycle in the graph, as the threads in wait order (each waits for the next, the last for the
     * first), starting from the alphabetically first thread in the cycle. Null when there is no cycle.
     */
    fun findCycle(): List<String>? {
        val next = edges()
        for (start in next.keys.sorted()) {
            val path = mutableListOf<String>()
            var cur: String? = start
            while (cur != null && cur !in path) {                  // each thread waits for at most one other
                path += cur
                cur = next[cur]
            }
            if (cur == null) continue                              // the chain ended at a running thread
            val cycle = path.drop(path.indexOf(cur))               // the part of the path that loops back
            val first = cycle.indexOf(cycle.min())
            return cycle.drop(first) + cycle.take(first)          // rotate so the smallest name leads
        }
        return null
    }
}

/** The four conditions that must all hold for a deadlock (Coffman et al., 1971). */
enum class Coffman { MUTUAL_EXCLUSION, HOLD_AND_WAIT, NO_PREEMPTION, CIRCULAR_WAIT }

/** Ways to make the transfer deadlock impossible. Each one breaks exactly one condition. */
enum class Fix {
    /** Lock the accounts in one global order (smaller id first), whatever the direction of the transfer. */
    LOCK_ORDERING,

    /** Take every lock you need at once, at the start, under one extra "prevention" lock. */
    ALL_LOCKS_AT_ONCE,

    /** `tryLock(timeout)` the second lock; on failure release the first, wait a random moment, retry. */
    TRY_LOCK_AND_BACK_OFF,

    /** No lock at all: update the balances with compare-and-swap (`AtomicLong`, `VarHandle`). */
    LOCK_FREE,
    ;

    /** The Coffman condition this fix takes away. */
    fun breaks(): Coffman = when (this) {
        LOCK_ORDERING -> Coffman.CIRCULAR_WAIT              // nobody can wait "backwards" in the order
        ALL_LOCKS_AT_ONCE -> Coffman.HOLD_AND_WAIT          // you never hold one lock while waiting for another
        TRY_LOCK_AND_BACK_OFF -> Coffman.NO_PREEMPTION      // the thread gives up a lock it holds
        LOCK_FREE -> Coffman.MUTUAL_EXCLUSION               // nothing is held exclusively
    }
}

/** One step of a thread in [Schedules]. */
sealed interface Op {
    data class Lock(val lock: String) : Op
    data class Unlock(val lock: String) : Op
}

/** Tries every order in which some threads' lock steps can run, like the interleaving widget in this lesson. */
object Schedules {
    /** How many complete schedules finished and how many ended with every unfinished thread blocked. */
    data class Outcome(val finished: Int, val deadlocked: Int, val firstDeadlock: List<String>?)

    /** Written for you: a depth-first search over every runnable choice. Threads block on a lock another thread holds. */
    fun explore(threads: Map<String, List<Op>>): Outcome {
        var finished = 0
        var deadlocked = 0
        var first: List<String>? = null
        fun go(pc: Map<String, Int>, owner: Map<String, String>, trace: List<String>) {
            val runnable = threads.keys.filter { t ->
                val op = threads.getValue(t).getOrNull(pc.getValue(t))
                op != null && !(op is Op.Lock && owner[op.lock] != null && owner[op.lock] != t)
            }
            if (runnable.isEmpty()) {
                if (threads.all { (t, ops) -> pc.getValue(t) >= ops.size }) finished++
                else { deadlocked++; if (first == null) first = trace }
                return
            }
            for (t in runnable) {
                val op = threads.getValue(t)[pc.getValue(t)]
                val nextOwner = when (op) {
                    is Op.Lock -> owner + (op.lock to t)
                    is Op.Unlock -> owner - op.lock
                }
                val label = when (op) { is Op.Lock -> "$t locks ${op.lock}"; is Op.Unlock -> "$t unlocks ${op.lock}" }
                go(pc + (t to pc.getValue(t) + 1), nextOwner, trace + label)
            }
        }
        go(threads.keys.associateWith { 0 }, emptyMap(), emptyList())
        return Outcome(finished, deadlocked, first)
    }

    /** The transfer from this lesson's demo: lock the source, then the target. Written for you. */
    fun transfer(from: String, to: String): List<Op> =
        listOf(Op.Lock(from), Op.Lock(to), Op.Unlock(to), Op.Unlock(from))

    /** The same transfer with [Fix.LOCK_ORDERING]: lock the smaller account id first, whichever way the money goes. */
    fun orderedTransfer(from: String, to: String): List<Op> {
        val (first, second) = if (from < to) from to to else to to from
        return listOf(Op.Lock(first), Op.Lock(second), Op.Unlock(second), Op.Unlock(first))
    }
}
