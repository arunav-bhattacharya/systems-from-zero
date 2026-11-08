package sfz.cons.l04

// The messages of Raft, as in Figure 2 of the paper. Done for you.

/** One log entry: the term of the leader that created it, and the command for the state machine. */
data class Entry(val term: Long, val command: String) {
    override fun toString() = "t$term:$command"
}

/** The command a new leader appends at the start of its term, so it can commit something from its own term. */
const val NO_OP = "no-op"

/** Every message carries the sender's current term. A node that sees a higher term moves to it at once. */
sealed interface Message {
    val term: Long
}

/** A candidate asks for a vote. [lastLogIndex] and [lastLogTerm] describe the end of the candidate's log. */
data class RequestVote(override val term: Long, val candidateId: Int, val lastLogIndex: Int, val lastLogTerm: Long) : Message

/** The answer to [RequestVote]. [term] is the voter's current term, so a stale candidate learns of a newer one. */
data class VoteReply(override val term: Long, val granted: Boolean) : Message

/**
 * The leader replicates log entries (or, with no entries, sends a heartbeat). [prevLogIndex] and [prevLogTerm]
 * name the entry just before [entries]; a follower accepts only if its own log has that entry with that term.
 * [leaderCommit] is the leader's commit index.
 */
data class AppendEntries(
    override val term: Long,
    val leaderId: Int,
    val prevLogIndex: Int,
    val prevLogTerm: Long,
    val entries: List<Entry>,
    val leaderCommit: Int,
) : Message

/**
 * The answer to [AppendEntries]. On success, [matchIndex] is the index of the last entry the follower now
 * knows matches the leader's log (`prevLogIndex + entries.size`). The paper's reply has only term and success;
 * real implementations add this so the leader can tell which request a late reply answers.
 */
data class AppendReply(override val term: Long, val success: Boolean, val matchIndex: Int) : Message

enum class Role { FOLLOWER, CANDIDATE, LEADER }

/**
 * Timing in simulated milliseconds. A follower that hears nothing from a leader for its election timeout, a
 * random value from [electionTimeoutMin] (inclusive) to [electionTimeoutMax] (exclusive), starts an election.
 * Equal bounds mean no randomness. A leader sends a heartbeat every [heartbeatInterval].
 */
data class Timing(
    val electionTimeoutMin: Long = 150,
    val electionTimeoutMax: Long = 300,
    val heartbeatInterval: Long = 50,
)
