package sfz.txn.l08

/**
 * A ballot orders proposals: the higher [round] wins, and on a tie the proposer's name decides, so
 * no two proposers ever hold the same ballot. Cassandra uses a time-based UUID for the same job.
 */
data class Ballot(val round: Int, val proposer: String) : Comparable<Ballot> {
    override fun compareTo(other: Ballot): Int = compareValuesBy(this, other, Ballot::round, Ballot::proposer)
    override fun toString() = "$round.$proposer"
}

/** A value proposed under a ballot. A null [value] means "the row doesn't exist". */
data class Proposal(val ballot: Ballot, val value: String?)

/** An acceptor's answer to `prepare`. */
sealed interface Promise {
    /**
     * "I promise to ignore every ballot lower than yours." It carries the proposal this acceptor
     * accepted but has not seen committed ([inProgress]), and the last one it saw committed.
     */
    data class Ok(val inProgress: Proposal?, val committed: Proposal?) : Promise

    /** "I have already promised [promised], which is at least as high as yours." */
    data class Rejected(val promised: Ballot) : Promise
}

/**
 * One replica of one partition. Cassandra keeps this state next to the row, in the `system.paxos`
 * table, which is why the trace of an LWT shows "Adding to paxos memtable".
 */
class Acceptor(val name: String) {
    var up: Boolean = true

    /** The highest ballot this acceptor has promised. */
    var promised: Ballot? = null

    /** The last proposal it accepted that it hasn't seen committed. It may already be the decision. */
    var inProgress: Proposal? = null

    /** The row as stored: the last committed proposal. */
    var committed: Proposal? = null

    /** Phase 1. Promise [ballot] if it is higher than every ballot promised so far. */
    fun prepare(ballot: Ballot): Promise {
        val already = promised
        if (already != null && ballot <= already) return Promise.Rejected(already) // an equal or newer proposer got here first
        promised = ballot                                                         // from now on, ignore anything lower
        return Promise.Ok(inProgress, committed)                                  // tell the proposer what might already be decided
    }

    /** Phase 3. Accept [proposal] unless a higher ballot has been promised since. */
    fun accept(proposal: Proposal): Boolean {
        val already = promised
        if (already != null && proposal.ballot < already) return false // someone newer prepared after this proposer did
        promised = proposal.ballot
        inProgress = proposal                                           // accepted, not yet known to be committed
        return true
    }

    /** Phase 4. Given: store the committed value if it is newer, and forget the proposal it settles. */
    fun commit(proposal: Proposal) {
        val c = committed
        if (c == null || c.ballot < proposal.ballot) committed = proposal
        val p = inProgress
        if (p != null && p.ballot <= proposal.ballot) inProgress = null
    }
}

/** What one compare-and-set did: the `[applied]` column of a Cassandra lightweight transaction, and more. */
sealed interface CasResult {
    /** The condition held, and the new value is committed. [roundTrips] counts the phases that sent messages. */
    data class Applied(val roundTrips: Int) : CasResult

    /** The condition was false. [current] is the value that made it false, as Cassandra returns the row with `[applied] = False`. */
    data class NotApplied(val current: String?, val roundTrips: Int) : CasResult

    /** A proposer with a higher ballot ([by]) got in the way. This attempt committed nothing of its own; retry. */
    data class Contended(val by: Ballot) : CasResult

    /** Fewer than a majority of acceptors were reachable. Nothing was attempted. */
    data object Unavailable : CasResult
}

/**
 * One partition's row, replicated on three acceptors, written only through Paxos compare-and-set:
 * a model of a Cassandra lightweight transaction (`IF NOT EXISTS`, `IF balance = ...`), Paxos v1.
 *
 * Your job: [Acceptor.prepare], [Acceptor.accept] and [compareAndSet]. Everything else is given.
 */
class PaxosRegister(val names: List<String> = listOf("A", "B", "C")) {
    val acceptors: List<Acceptor> = names.map(::Acceptor)

    /** 2 of 3. Any two majorities share at least one acceptor. */
    val majority: Int = names.size / 2 + 1

    fun acceptor(name: String): Acceptor = acceptors.first { it.name == name }

    fun fail(name: String) {
        acceptor(name).up = false
    }

    fun recover(name: String) {
        acceptor(name).up = true
    }

    /** The committed value on one replica, as a plain read at consistency ONE would see it. */
    fun valueAt(name: String): String? = acceptor(name).committed?.value

    /** The acceptors a message can reach: up, and in [reaches]. Given. */
    fun reachable(reaches: Set<String>): List<Acceptor> = acceptors.filter { it.up && it.name in reaches }

    /** A ballot higher than any promised so far. Given (a real proposer learns this from rejections). */
    fun nextBallot(proposer: String): Ballot =
        Ballot(1 + (acceptors.mapNotNull { it.promised?.round }.maxOrNull() ?: 0), proposer)

    /** The newest committed value among [from]: the read step of an LWT, at SERIAL. Given. */
    fun read(from: List<Acceptor>): String? = from.mapNotNull { it.committed }.maxByOrNull { it.ballot }?.value

    /**
     * Sets the row to [newValue] if it currently equals [expected] (null = "IF NOT EXISTS").
     *
     * 0. Fewer than [majority] acceptors reachable: [CasResult.Unavailable].
     * 1. Prepare: take [nextBallot] and send `prepare` to every reachable acceptor (one round trip).
     *    Fewer than [majority] `Ok`s: [CasResult.Contended], with the highest `promised` among the rejections.
     *    If an `Ok` carries an `inProgress` proposal whose ballot is higher than every `committed` ballot in
     *    the replies, it may already be the decision: take the highest such proposal, `accept` its VALUE
     *    under YOUR ballot (a round trip; fewer than [majority] accepts: Contended), `commit` it to every
     *    reachable acceptor (a round trip), then start again from step 1 with a new ballot.
     * 2. Read: [read] the reachable acceptors (a round trip). Not equal to [expected]: [CasResult.NotApplied].
     * 3. Call [beforePropose] (tests use it to let another proposer run), then propose: `accept` a
     *    `Proposal(ballot, newValue)` on every reachable acceptor (a round trip). Fewer than [majority]
     *    accepted: [CasResult.Contended], with the highest `promised` among the acceptors that refused.
     * 4. Commit: `commit` it to every reachable acceptor (a round trip). [CasResult.Applied].
     *
     * Count every round trip, including the ones spent finishing someone else's proposal.
     */
    fun compareAndSet(
        proposer: String,
        expected: String?,
        newValue: String,
        reaches: Set<String> = names.toSet(),
        beforePropose: () -> Unit = {},
    ): CasResult {
        var trips = 0
        while (true) {
            val replicas = reachable(reaches)
            if (replicas.size < majority) return CasResult.Unavailable // the coordinator checks before it tries

            // 1. prepare / promise
            val ballot = nextBallot(proposer)
            trips++
            val promises = replicas.map { it.prepare(ballot) }
            val oks = promises.filterIsInstance<Promise.Ok>()
            if (oks.size < majority) {
                return CasResult.Contended(promises.filterIsInstance<Promise.Rejected>().maxOf { it.promised })
            }

            // an accepted proposal that nobody in the quorum has seen committed may already be chosen:
            // Paxos's one rule is that it must be finished, not overwritten
            val lastCommit = oks.mapNotNull { it.committed?.ballot }.maxOrNull()
            val unfinished = oks.mapNotNull { it.inProgress }
                .filter { lastCommit == null || it.ballot > lastCommit }
                .maxByOrNull { it.ballot }
            if (unfinished != null) {
                val again = Proposal(ballot, unfinished.value) // the old value, under our ballot
                trips++
                if (replicas.count { it.accept(again) } < majority) return CasResult.Contended(highestPromise(replicas))
                trips++
                replicas.forEach { it.commit(again) }
                continue // now start our own operation with a fresh ballot
            }

            // 2. read the current value and check the condition
            trips++
            val current = read(replicas)
            if (current != expected) return CasResult.NotApplied(current, trips)

            // 3. propose / accept
            beforePropose()
            val proposal = Proposal(ballot, newValue)
            trips++
            if (replicas.count { it.accept(proposal) } < majority) return CasResult.Contended(highestPromise(replicas))

            // 4. commit
            trips++
            replicas.forEach { it.commit(proposal) }
            return CasResult.Applied(trips)
        }
    }

    /** The highest ballot promised by any of [replicas], to report who won a contention. Given. */
    fun highestPromise(replicas: List<Acceptor>): Ballot = replicas.mapNotNull { it.promised }.max()
}
