package sfz.derive.l04

import kotlin.random.Random

/** A user asks for a handle, such as `@ana`. [requestId] is made by the client and kept across retries. */
data class Claim(val requestId: String, val userId: String, val username: String)

/** The answer a client waits for. */
sealed interface Decision {
    val requestId: String
    val username: String
}

data class Granted(override val requestId: String, override val username: String, val userId: String) : Decision

data class Rejected(override val requestId: String, override val username: String, val takenBy: String) : Decision

/** What a run produced: every decision a client received, and how long each client waited (in scheduler steps). */
class ClaimRun(val decisions: List<Decision>, val waits: List<Long>) {
    /** Handles granted to more than one user, counted as extra owners: two owners of `@ana` is 1. */
    val duplicates: Int
        get() = decisions.filterIsInstance<Granted>()
            .groupBy { it.username }
            .values.sumOf { grants -> grants.map { it.userId }.distinct().size - 1 }

    val granted: Int get() = decisions.count { it is Granted }
}

/** [users] users, each claiming one handle drawn from [names] popular ones, so many users want the same handle. */
object Workload {
    fun claims(seed: Long, users: Int = 2_000, names: Int = 200): List<Claim> {
        val rnd = Random(seed)
        return (0 until users).map { u -> Claim("req-$u", "u-$u", "name-${rnd.nextInt(names)}") }
    }
}

/**
 * The race (finished). [servers] app servers share one table that has no unique constraint. Each
 * server checks whether the handle is free, then inserts it. Between the SELECT and the INSERT
 * there is a round trip to the database (the `yield`), and in that gap another server can run
 * its own check and see the handle as free too.
 */
fun checkThenInsert(claims: List<Claim>, servers: Int, seed: Long): ClaimRun {
    val table = LinkedHashMap<String, MutableList<String>>()    // handle -> the users holding it
    val decisions = ArrayList<Decision>()
    val waits = ArrayList<Long>()
    val sched = Scheduler(seed)
    for (s in 0 until servers) {
        val mine = claims.filterIndexed { i, _ -> i % servers == s }
        sched.spawn {
            for (c in mine) {
                val start = sched.now
                val holder = table[c.username]?.firstOrNull()   // SELECT user_id FROM handles WHERE name = ?
                yield(Unit)                                     // the round trip: anyone may run here
                if (holder == null) {
                    table.getOrPut(c.username) { mutableListOf() } += c.userId   // INSERT INTO handles ...
                    decisions += Granted(c.requestId, c.username, c.userId)
                } else {
                    decisions += Rejected(c.requestId, c.username, holder)
                }
                waits += sched.now - start
                yield(Unit)
            }
        }
    }
    sched.run()
    return ClaimRun(decisions, waits)
}

/**
 * Exercise 1. Which of [partitions] partitions a key goes to: the key's `hashCode()` modulo the
 * partition count, always in `0 until partitions`.
 *
 * Use `Math.floorMod`, not `abs(hashCode) % partitions`: `abs(Int.MIN_VALUE)` is still negative.
 */
fun partitionFor(key: String, partitions: Int): Int =
    Math.floorMod(key.hashCode(), partitions)                    // same key, same partition, every time

/**
 * Exercise 2. One partition's processor. It is single-threaded and reads its partition in order,
 * so for every handle routed to it, it alone decides, one claim at a time. That is the whole trick.
 *
 * Its state is derived only from the claims it has read, so a fresh processor that replays the
 * partition from offset 0 rebuilds the same state and makes the same decisions.
 */
class ClaimProcessor {
    private val owner = HashMap<String, String>()               // handle -> userId that holds it
    private val decided = HashMap<String, Decision>()           // requestId -> the answer already given

    /**
     * Decides one claim:
     * - a requestId it has seen before gets exactly the answer it got the first time (a redelivery
     *   or a client retry must not change anything);
     * - a free handle, or one this same user already holds, is [Granted] to the claimant;
     * - otherwise it is [Rejected], naming the user who holds it.
     */
    fun decide(claim: Claim): Decision {
        decided[claim.requestId]?.let { return it }             // seen it: same answer, no new effect
        val holder = owner[claim.username]
        val decision = if (holder == null || holder == claim.userId) {
            owner[claim.username] = claim.userId                // the first claim in log order wins
            Granted(claim.requestId, claim.username, claim.userId)
        } else {
            Rejected(claim.requestId, claim.username, holder)
        }
        decided[claim.requestId] = decision
        return decision
    }
}

/**
 * Claims through a partitioned log (finished). Each of [clients] clients appends its claim to the
 * partition that [keyOf] picks, then waits for its decision. One [ClaimProcessor] per partition
 * reads that partition in order and answers. Route by the handle, and every claim for one handle
 * meets the same processor. Route by anything else, and two processors can each grant it.
 */
fun throughLog(
    claims: List<Claim>,
    clients: Int,
    partitions: Int,
    seed: Long,
    keyOf: (Claim) -> String = Claim::username,
): ClaimRun {
    val logs = List(partitions) { ArrayList<Claim>() }
    val replies = HashMap<String, Decision>()
    val decisions = ArrayList<Decision>()
    val waits = ArrayList<Long>()
    var clientsDone = 0
    val sched = Scheduler(seed)
    for (c in 0 until clients) {
        val mine = claims.filterIndexed { i, _ -> i % clients == c }
        sched.spawn {
            for (claim in mine) {
                val start = sched.now
                logs[partitionFor(keyOf(claim), partitions)] += claim   // one append: the request is now durable
                yield(Unit)
                while (claim.requestId !in replies) yield(Unit)          // the timeliness cost: wait for the answer
                decisions += replies.getValue(claim.requestId)
                waits += sched.now - start
            }
            clientsDone++
        }
    }
    for (p in 0 until partitions) {
        sched.spawn {
            val processor = ClaimProcessor()
            var offset = 0
            while (clientsDone < clients || offset < logs[p].size) {
                if (offset < logs[p].size) {
                    val d = processor.decide(logs[p][offset++])
                    replies[d.requestId] = d
                }
                yield(Unit)
            }
        }
    }
    sched.run()
    return ClaimRun(decisions, waits)
}
