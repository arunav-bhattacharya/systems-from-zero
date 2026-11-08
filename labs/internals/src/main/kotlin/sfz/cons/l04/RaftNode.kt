package sfz.cons.l04

import kotlin.random.Random

// Lesson cons-04 lab (Consensus with Raft): one Raft server.
// Your job: the four handlers at the top of RaftNode: handleRequestVote, handleAppendEntries,
// handleAppendReply and advanceCommitIndex. Everything below the "provided" line is done: timers,
// starting an election, counting votes, becoming leader, sending AppendEntries, applying committed
// entries, and stepping down on a higher term. The Cluster in Cluster.kt runs five of these on a
// simulated network.

/**
 * One server of a Raft cluster of [clusterSize] servers with ids 0 until [clusterSize]. Log indexes start at
 * 1, as in the paper: `log[0]` holds index 1, and index 0 means "before the first entry", with term 0.
 *
 * The node never blocks and has no threads: [receive] handles one message and [tick] lets time pass, and
 * both send messages through [send]. That keeps every run deterministic.
 */
class RaftNode(
    val id: Int,
    val clusterSize: Int,
    private val random: Random,
    private val timing: Timing = Timing(),
    private val send: (to: Int, msg: Message) -> Unit = { _, _ -> },
    private val trace: (String) -> Unit = {},
) {
    // Persistent state: on stable storage, survives a crash. (The simulator keeps it across restart().)
    var currentTerm = 0L
    var votedFor: Int? = null
    val log = ArrayList<Entry>()

    // Volatile state: lost in a crash.
    var role = Role.FOLLOWER
    var leaderId: Int? = null
    var commitIndex = 0

    /** The state machine: every committed command, applied in log order. */
    val applied = ArrayList<String>()

    // Volatile state on a leader, reset when it wins an election. matchIndex[id] is the leader's own last index.
    val nextIndex = IntArray(clusterSize)
    val matchIndex = IntArray(clusterSize)

    val lastLogIndex: Int get() = log.size

    /** The term of the entry at [index], or 0 for index 0. */
    fun termAt(index: Int): Long = if (index == 0) 0L else log[index - 1].term

    /** How many servers make a majority: 3 of 5, 2 of 3. */
    val majority: Int get() = clusterSize / 2 + 1

    /**
     * A candidate asks for this node's vote. [receive] has already moved [currentTerm] up to `req.term` if
     * that was newer (and cleared [votedFor]). Grant the vote only if all of these hold:
     * 1. `req.term` is not older than [currentTerm];
     * 2. this node hasn't voted in this term, or voted for this same candidate ([votedFor]);
     * 3. the candidate's log is at least as up to date as ours: its last term is higher than ours, or the
     *    last terms are equal and its log is at least as long.
     * When granting, set [votedFor] (it is persistent: one vote per term, even across a crash).
     * Reply with our [currentTerm] either way.
     */
    fun handleRequestVote(req: RequestVote): VoteReply {
        TODO("older term: refuse; grant only if votedFor is null or this candidate AND its log is at least as up to date (higher last term, or same last term and at least as long); set votedFor when granting; reply with currentTerm")
    }

    /**
     * The leader sends entries (or a heartbeat). [receive] has already moved [currentTerm] up if `req.term`
     * was newer. Follow the paper's receiver rules:
     * 1. `req.term` older than [currentTerm]: refuse (a deposed leader). Reply `AppendReply(currentTerm, false, 0)`.
     * 2. The log matching check: refuse unless our log has an entry at `req.prevLogIndex` whose term is
     *    `req.prevLogTerm` (index 0 always matches).
     * 3. For each entry, at index prevLogIndex + 1, + 2, ...: if we already have an entry there with the SAME
     *    term, keep it; if the term differs, delete that entry and everything after it; then append what we
     *    don't have. Never delete entries that match: a late, shorter copy of an old request must not cut
     *    the log.
     * 4. If `req.leaderCommit` is greater than [commitIndex], raise [commitIndex] to
     *    min(leaderCommit, index of the last new entry). Never lower it.
     * 5. Reply `AppendReply(currentTerm, true, prevLogIndex + entries.size)`.
     */
    fun handleAppendEntries(req: AppendEntries): AppendReply {
        TODO("older term: refuse; no entry at prevLogIndex with prevLogTerm: refuse; walk the entries: keep same-term ones, cut the log at the first conflict, append the rest; raise commitIndex to min(leaderCommit, last new index); reply success with prevLogIndex + entries.size")
    }

    /**
     * The leader handles a follower's answer to AppendEntries ([receive] checked that we are still the leader
     * of `reply.term`).
     * - Success: the follower's log matches ours up to `reply.matchIndex`. Raise `matchIndex[from]` to it
     *   (replies can arrive out of order, so never lower it) and set `nextIndex[from]` to `matchIndex[from] + 1`.
     * - Failure: the logs differ at `nextIndex[from] - 1`. Move `nextIndex[from]` back by one, but not below
     *   `matchIndex[from] + 1`. ([receive] then sends the follower an AppendEntries from the new nextIndex.)
     */
    fun handleAppendReply(from: Int, reply: AppendReply) {
        TODO("success: matchIndex[from] = max(old, reply.matchIndex), nextIndex[from] = matchIndex[from] + 1; failure: nextIndex[from] = max(matchIndex[from] + 1, nextIndex[from] - 1)")
    }

    /**
     * The commit rule, run by the leader after every successful reply. Find the highest index N above
     * [commitIndex] such that a majority of servers have it (`matchIndex[i] >= N`, counting our own
     * `matchIndex[id]`) AND `log[N]` is from [currentTerm]. Set [commitIndex] to N. Entries from earlier terms
     * are never committed by counting copies: they become committed when an entry of the current term after
     * them is (Figure 8 of the paper shows what goes wrong otherwise).
     */
    fun advanceCommitIndex() {
        TODO("for n from lastLogIndex down to commitIndex + 1: stop at an entry not from currentTerm; if matchIndex has a majority >= n, set commitIndex = n and stop")
    }

    // ------------------------------------------------------------------------------------------------- provided

    private val votes = HashSet<Int>()
    private var electionDeadline = 0L
    private var heartbeatDue = 0L

    /** Starts the election timer. Every node starts as a follower in term 0. */
    fun start(now: Long) = resetElectionTimer(now)

    /** Lets time pass: a leader sends heartbeats, a follower or candidate whose timer ran out starts an election. */
    fun tick(now: Long) {
        if (role == Role.LEADER) {
            if (now >= heartbeatDue) {
                broadcastAppendEntries()
                heartbeatDue = now + timing.heartbeatInterval
            }
        } else if (now >= electionDeadline) {
            startElection(now)
        }
    }

    /** Handles one message from server [from]. */
    fun receive(from: Int, msg: Message, now: Long) {
        if (msg.term > currentTerm) {                               // a newer term: become its follower
            if (role != Role.FOLLOWER) trace("steps down: saw term ${msg.term} from ${name(from)}")
            currentTerm = msg.term
            votedFor = null
            role = Role.FOLLOWER
            leaderId = null
        }
        when (msg) {
            is RequestVote -> {
                val reply = handleRequestVote(msg)
                if (reply.granted) {
                    trace("votes for ${name(msg.candidateId)} in term ${msg.term}")
                    resetElectionTimer(now)
                } else if (msg.term == currentTerm) {
                    trace("refuses ${name(msg.candidateId)} in term ${msg.term}")
                }
                send(from, reply)
            }
            is VoteReply -> if (role == Role.CANDIDATE && msg.term == currentTerm && msg.granted) {
                votes += from
                if (votes.size >= majority) becomeLeader(now)
            }
            is AppendEntries -> {
                if (msg.term == currentTerm) {                      // from the leader of our term
                    if (role == Role.CANDIDATE) role = Role.FOLLOWER
                    leaderId = msg.leaderId
                    resetElectionTimer(now)
                }
                val reply = handleAppendEntries(msg)
                if (!reply.success && msg.term == currentTerm) {
                    trace("refuses entries after index ${msg.prevLogIndex} (term ${msg.prevLogTerm}): no matching entry")
                }
                send(from, reply)
            }
            is AppendReply -> if (role == Role.LEADER && msg.term == currentTerm) {
                handleAppendReply(from, msg)
                advanceCommitIndex()
                if (!msg.success) sendAppendEntries(from)           // retry at once from the lower nextIndex
            }
        }
        applyCommitted()
    }

    /** A client command. Only the leader accepts it: it appends it and replicates it. Returns its index, or null. */
    fun propose(command: String): Int? {
        if (role != Role.LEADER) return null
        log += Entry(currentTerm, command)
        matchIndex[id] = lastLogIndex
        advanceCommitIndex()                                        // a one-server cluster commits at once
        applyCommitted()
        broadcastAppendEntries()
        return lastLogIndex
    }

    /** Comes back after a crash: persistent state (term, vote, log) is kept, everything else starts over. */
    fun restart(now: Long) {
        role = Role.FOLLOWER
        leaderId = null
        commitIndex = 0
        applied.clear()
        votes.clear()
        nextIndex.fill(0)
        matchIndex.fill(0)
        resetElectionTimer(now)
    }

    private fun resetElectionTimer(now: Long) {
        val span = timing.electionTimeoutMax - timing.electionTimeoutMin
        electionDeadline = now + timing.electionTimeoutMin + if (span > 0) random.nextLong(span) else 0L
    }

    private fun startElection(now: Long) {
        currentTerm++
        role = Role.CANDIDATE
        votedFor = id
        leaderId = null
        votes.clear()
        votes += id
        resetElectionTimer(now)                                     // if this election fails, try again later
        trace("times out, starts an election for term $currentTerm")
        if (votes.size >= majority) return becomeLeader(now)
        val req = RequestVote(currentTerm, id, lastLogIndex, termAt(lastLogIndex))
        for (peer in 0 until clusterSize) if (peer != id) send(peer, req)
    }

    private fun becomeLeader(now: Long) {
        role = Role.LEADER
        leaderId = id
        trace("wins term $currentTerm with ${votes.size} votes")
        nextIndex.fill(lastLogIndex + 1)
        matchIndex.fill(0)
        log += Entry(currentTerm, NO_OP)                            // section 8 of the paper: an entry of our own term
        matchIndex[id] = lastLogIndex
        advanceCommitIndex()
        broadcastAppendEntries()
        heartbeatDue = now + timing.heartbeatInterval
    }

    private fun broadcastAppendEntries() {
        for (peer in 0 until clusterSize) if (peer != id) sendAppendEntries(peer)
    }

    private fun sendAppendEntries(peer: Int) {
        val prev = nextIndex[peer] - 1
        send(peer, AppendEntries(currentTerm, id, prev, termAt(prev), log.subList(prev, log.size).toList(), commitIndex))
    }

    private fun applyCommitted() {
        while (applied.size < commitIndex) applied += log[applied.size].command
    }

    override fun toString() = "${name(id)}($role, term $currentTerm, log $log, commit $commitIndex)"
}

/** Servers are printed as n1, n2, ...: server id 0 is n1. */
fun name(id: Int) = "n${id + 1}"
