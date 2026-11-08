package sfz.cons.l04

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import kotlin.random.Random

class RaftTest {
    /** A lone server whose outgoing messages land in [sent], so a test can read its replies. */
    private class Probe(id: Int = 0, size: Int = 5) {
        val sent = ArrayList<Pair<Int, Message>>()
        val node = RaftNode(id, size, Random(0), send = { to, m -> sent += to to m })
        fun deliver(from: Int, msg: Message): Message {
            sent.clear()
            node.receive(from, msg, now = 1)
            return sent.single { it.first == from }.second
        }
    }

    private fun entries(vararg terms: Long) = terms.mapIndexed { i, t -> Entry(t, "c${i + 1}") }

    // ---------------------------------------------------------------- RequestVote

    @Test
    fun `a server votes for the first candidate of a term and refuses a second`() {
        val p = Probe()
        val first = p.deliver(1, RequestVote(term = 1, candidateId = 1, lastLogIndex = 0, lastLogTerm = 0)) as VoteReply
        assertThat(first.granted).isTrue()
        assertThat(p.node.votedFor).isEqualTo(1)
        assertThat(p.node.currentTerm).isEqualTo(1)
        val second = p.deliver(2, RequestVote(term = 1, candidateId = 2, lastLogIndex = 0, lastLogTerm = 0)) as VoteReply
        assertThat(second.granted).`as`("a second candidate in the same term").isFalse()
        val again = p.deliver(1, RequestVote(term = 1, candidateId = 1, lastLogIndex = 0, lastLogTerm = 0)) as VoteReply
        assertThat(again.granted).`as`("the same candidate asking again (its first reply was lost)").isTrue()
        val next = p.deliver(2, RequestVote(term = 2, candidateId = 2, lastLogIndex = 0, lastLogTerm = 0)) as VoteReply
        assertThat(next.granted).`as`("a new term, a new vote").isTrue()
        assertThat(p.node.votedFor).isEqualTo(2)
    }

    @Test
    fun `a server refuses a candidate whose log is behind its own`() {
        val p = Probe()
        p.node.currentTerm = 2
        p.node.log += entries(1, 1, 2)                        // last entry: index 3, term 2
        val olderLastTerm = p.deliver(1, RequestVote(term = 3, candidateId = 1, lastLogIndex = 9, lastLogTerm = 1)) as VoteReply
        assertThat(olderLastTerm.granted).`as`("a longer log with an older last term").isFalse()
        val shorter = p.deliver(2, RequestVote(term = 3, candidateId = 2, lastLogIndex = 2, lastLogTerm = 2)) as VoteReply
        assertThat(shorter.granted).`as`("same last term, shorter log").isFalse()
        val asGood = p.deliver(3, RequestVote(term = 3, candidateId = 3, lastLogIndex = 3, lastLogTerm = 2)) as VoteReply
        assertThat(asGood.granted).`as`("same last term, same length").isTrue()
        assertThat(p.node.currentTerm).isEqualTo(3)
    }

    @Test
    fun `a request from an older term is refused and the reply carries the newer term`() {
        val p = Probe()
        p.node.currentTerm = 3
        p.node.log += entries(1, 3)
        val vote = p.deliver(1, RequestVote(term = 2, candidateId = 1, lastLogIndex = 5, lastLogTerm = 2)) as VoteReply
        assertThat(vote.granted).isFalse()
        assertThat(vote.term).isEqualTo(3)
        val append = p.deliver(1, AppendEntries(term = 2, leaderId = 1, prevLogIndex = 0, prevLogTerm = 0, entries = entries(2), leaderCommit = 1)) as AppendReply
        assertThat(append.success).`as`("entries from a deposed leader").isFalse()
        assertThat(append.term).isEqualTo(3)
        assertThat(p.node.log).isEqualTo(entries(1, 3))
        assertThat(p.node.commitIndex).isZero()
    }

    // ---------------------------------------------------------------- AppendEntries on a follower

    @Test
    fun `append entries is refused when the log has no matching entry at prevLogIndex`() {
        val p = Probe()
        p.node.currentTerm = 2
        p.node.log += entries(1, 1)
        val gap = p.deliver(1, AppendEntries(2, 1, prevLogIndex = 3, prevLogTerm = 2, entries = listOf(Entry(2, "x")), leaderCommit = 0)) as AppendReply
        assertThat(gap.success).`as`("our log has no index 3").isFalse()
        val wrongTerm = p.deliver(1, AppendEntries(2, 1, prevLogIndex = 2, prevLogTerm = 2, entries = listOf(Entry(2, "x")), leaderCommit = 0)) as AppendReply
        assertThat(wrongTerm.success).`as`("index 2 holds term 1, not 2").isFalse()
        assertThat(p.node.log).hasSize(2)
        val ok = p.deliver(1, AppendEntries(2, 1, prevLogIndex = 2, prevLogTerm = 1, entries = listOf(Entry(2, "x")), leaderCommit = 0)) as AppendReply
        assertThat(ok.success).isTrue()
        assertThat(ok.matchIndex).isEqualTo(3)
        assertThat(p.node.log.last()).isEqualTo(Entry(2, "x"))
        val heartbeat = p.deliver(1, AppendEntries(2, 1, prevLogIndex = 0, prevLogTerm = 0, entries = emptyList(), leaderCommit = 0)) as AppendReply
        assertThat(heartbeat.success).`as`("index 0 always matches").isTrue()
        assertThat(p.node.log).`as`("an empty heartbeat deletes nothing").hasSize(3)
    }

    @Test
    fun `a conflicting suffix is cut off and replaced, and a matching one is kept`() {
        val p = Probe()
        p.node.currentTerm = 2
        p.node.log += entries(1, 1, 1, 2, 2)                 // indexes 4 and 5 from a leader of term 2 that never committed them
        val fresh = listOf(Entry(3, "a"), Entry(3, "b"))
        val r = p.deliver(1, AppendEntries(3, 1, prevLogIndex = 3, prevLogTerm = 1, entries = fresh, leaderCommit = 0)) as AppendReply
        assertThat(r.success).isTrue()
        assertThat(p.node.log.map { it.term }).containsExactly(1L, 1L, 1L, 3L, 3L)
        assertThat(p.node.log.takeLast(2)).isEqualTo(fresh)
        val late = p.deliver(1, AppendEntries(3, 1, prevLogIndex = 3, prevLogTerm = 1, entries = fresh.take(1), leaderCommit = 0)) as AppendReply
        assertThat(late.success).isTrue()
        assertThat(late.matchIndex).isEqualTo(4)
        assertThat(p.node.log).`as`("a late copy of an older, shorter request must not cut index 5").hasSize(5)
    }

    @Test
    fun `a follower commits up to leaderCommit, but not past its last new entry, and never goes back`() {
        val p = Probe()
        p.deliver(1, AppendEntries(1, 1, 0, 0, entries(1, 1, 1, 1), leaderCommit = 10))
        assertThat(p.node.commitIndex).isEqualTo(4)
        assertThat(p.node.applied).containsExactly("c1", "c2", "c3", "c4")
        p.deliver(1, AppendEntries(1, 1, prevLogIndex = 1, prevLogTerm = 1, entries = emptyList(), leaderCommit = 3))
        assertThat(p.node.commitIndex).`as`("an old heartbeat arriving late").isEqualTo(4)
        val p2 = Probe()
        p2.deliver(1, AppendEntries(1, 1, 0, 0, entries(1, 1, 1), leaderCommit = 2))
        assertThat(p2.node.commitIndex).isEqualTo(2)
        assertThat(p2.node.applied).containsExactly("c1", "c2")
    }

    // ---------------------------------------------------------------- the leader's side

    /** Server 0 as the leader of [term] with [log], every follower's nextIndex just past it. */
    private fun leader(term: Long, vararg logTerms: Long): RaftNode {
        val n = RaftNode(0, 5, Random(0))
        n.currentTerm = term
        n.role = Role.LEADER
        n.log += entries(*logTerms)
        n.nextIndex.fill(n.lastLogIndex + 1)
        n.matchIndex[0] = n.lastLogIndex
        return n
    }

    @Test
    fun `the leader backs nextIndex off on a refusal and records matchIndex on success`() {
        val n = leader(2, 1, 1, 2, 2, 2)
        n.handleAppendReply(1, AppendReply(2, false, 0))
        assertThat(n.nextIndex[1]).isEqualTo(5)
        n.handleAppendReply(1, AppendReply(2, false, 0))
        assertThat(n.nextIndex[1]).isEqualTo(4)
        n.handleAppendReply(1, AppendReply(2, true, 5))
        assertThat(n.matchIndex[1]).isEqualTo(5)
        assertThat(n.nextIndex[1]).isEqualTo(6)
        n.handleAppendReply(1, AppendReply(2, true, 3))
        assertThat(n.matchIndex[1]).`as`("a late reply to an older request").isEqualTo(5)
        assertThat(n.nextIndex[1]).isEqualTo(6)
        n.handleAppendReply(1, AppendReply(2, false, 0))
        assertThat(n.nextIndex[1]).`as`("never below matchIndex + 1").isEqualTo(6)
    }

    @Test
    fun `the leader commits an entry once a majority stores it`() {
        val n = leader(2, 1, 2, 2)
        n.matchIndex[1] = 3
        n.advanceCommitIndex()
        assertThat(n.commitIndex).`as`("2 of 5 servers have index 3").isZero()
        n.matchIndex[2] = 2
        n.advanceCommitIndex()
        assertThat(n.commitIndex).`as`("3 of 5 have index 2").isEqualTo(2)
        n.matchIndex[3] = 3
        n.advanceCommitIndex()
        assertThat(n.commitIndex).isEqualTo(3)
    }

    @Test
    fun `the leader never commits an entry of an earlier term by counting copies`() {
        // Figure 8 of the Raft paper: the leader of term 4 holds an entry from term 2 that 3 of 5 servers have.
        val n = leader(4, 1, 2)
        n.matchIndex[1] = 2
        n.matchIndex[2] = 2
        n.advanceCommitIndex()
        assertThat(n.commitIndex).`as`("index 2 is from term 2, so its copies don't count").isZero()
        n.log += Entry(4, "x")
        n.matchIndex[0] = 3
        n.matchIndex[1] = 3
        n.advanceCommitIndex()
        assertThat(n.commitIndex).`as`("index 3 is on 2 of 5").isZero()
        n.matchIndex[2] = 3
        n.advanceCommitIndex()
        assertThat(n.commitIndex).`as`("index 3, from term 4, on 3 of 5: it and everything before it").isEqualTo(3)
    }

    // ---------------------------------------------------------------- whole clusters

    @Test
    fun `a five-server cluster elects one leader and the others follow it`() {
        val c = Cluster(seed = 1)
        assertThat(c.runUntil(2_000) { it.leader() != null }).`as`("a leader within 2 seconds").isTrue()
        c.runFor(200)
        val leader = c.leader()!!
        for (n in c.nodes) {
            assertThat(n.currentTerm).isEqualTo(leader.currentTerm)
            if (n !== leader) {
                assertThat(n.role).isEqualTo(Role.FOLLOWER)
                assertThat(n.leaderId).isEqualTo(leader.id)
            }
            assertThat(n.log).`as`("everyone has the leader's no-op").isEqualTo(leader.log)
        }
        assertThat(c.violations).isEmpty()
    }

    @Test
    fun `every server applies the same commands in the same order, despite lost messages`() {
        val c = Cluster(seed = 2, lossRate = 0.1)
        c.runUntil(3_000) { it.leader() != null }
        repeat(20) {
            c.propose("pay-$it")
            c.runFor(15)
        }
        c.runFor(2_000)
        val expected = (0 until 20).map { "pay-$it" }
        for (n in c.nodes) {
            assertThat(n.applied.filter { it != NO_OP }).`as`("commands applied by ${name(n.id)}").isEqualTo(expected)
        }
        assertThat(c.violations).isEmpty()
    }

    @Test
    fun `a crashed leader is replaced, and every committed entry survives`() {
        val c = Cluster(seed = 3)
        c.runUntil(2_000) { it.leader() != null }
        repeat(5) { c.propose("pay-$it") }
        c.runUntil(1_000) { cl -> cl.leader()!!.commitIndex == cl.leader()!!.lastLogIndex }
        val old = c.leader()!!
        val committed = old.applied.toList()
        c.crash(old.id)
        assertThat(c.runUntil(2_000) { it.leader() != null }).`as`("a new leader").isTrue()
        val new = c.leader()!!
        assertThat(new.id).isNotEqualTo(old.id)
        assertThat(new.currentTerm).isGreaterThan(old.currentTerm)
        assertThat(new.log.map { it.command }).containsSubsequence(committed)
        repeat(3) { c.propose("after-$it") }
        c.restart(old.id)
        c.runFor(1_000)
        val commands = c.nodes[old.id].applied.filter { it != NO_OP }
        assertThat(commands).isEqualTo((0 until 5).map { "pay-$it" } + (0 until 3).map { "after-$it" })
        for (n in c.nodes) assertThat(n.applied).isEqualTo(c.nodes[old.id].applied)
        assertThat(c.violations).isEmpty()
    }

    @Test
    fun `a leader cut off from the others loses the entries it could not commit`() {
        val c = Cluster(seed = 4)
        c.runUntil(2_000) { it.leader() != null }
        c.propose("pay-1")
        c.runFor(100)
        val old = c.leader()!!
        c.isolate(old.id)
        c.proposeTo(old.id, "lost")                               // a client that still talks to the old leader
        assertThat(c.runUntil(2_000) { it.leader() != null }).isTrue()
        c.propose("kept")
        c.runFor(200)
        assertThat(old.role).`as`("cut off, it still believes it leads").isEqualTo(Role.LEADER)
        assertThat(old.commitIndex).isLessThan(old.lastLogIndex)
        c.heal(old.id)
        c.runFor(500)
        assertThat(old.role).isEqualTo(Role.FOLLOWER)
        for (n in c.nodes) {
            assertThat(n.log.map { it.command }).`as`("log of ${name(n.id)}").contains("pay-1", "kept").doesNotContain("lost")
            assertThat(n.log).isEqualTo(c.leader()!!.log)
        }
        assertThat(c.violations).isEmpty()
    }

    @Test
    fun `random crashes and lost messages never break safety`() {
        for (seed in 10L..14L) {
            val c = Cluster(seed = seed, lossRate = 0.15)
            val chaos = Random(seed)
            var proposed = 0
            for (round in 0 until 30) {
                if (c.propose("pay-$proposed") != null) proposed++
                val victim = chaos.nextInt(5)
                when {
                    !c.isUp(victim) -> c.restart(victim)
                    (0 until 5).count { c.isUp(it) } > 3 && chaos.nextInt(3) == 0 -> c.crash(victim)
                }
                c.runFor(100)
            }
            (0 until 5).filter { !c.isUp(it) }.forEach { c.restart(it) }
            c.lossRate = 0.0
            c.runUntil(3_000) { it.leader() != null }
            c.propose("last")
            c.runFor(1_500)
            assertThat(c.violations).`as`("seed $seed").isEmpty()
            val reference = c.leader()!!.applied
            assertThat(reference).`as`("seed $seed: the cluster still makes progress").contains("last")
            for (n in c.nodes) assertThat(n.applied).`as`("seed $seed, ${name(n.id)}").isEqualTo(reference)
            assertThat(reference.take(c.committedEntries().size)).isEqualTo(c.committedEntries().map { it.command })
        }
    }
}
