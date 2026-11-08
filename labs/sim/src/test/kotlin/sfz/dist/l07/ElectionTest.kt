package sfz.dist.l07

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test

/**
 * Exercises 2 and 3: the same election, checked under crash-stop and crash-recovery. The safety
 * rule is "at most one node ever wins the term". Every test explores every reachable state, so a
 * pass means no order of messages and no moment for the crash breaks the rule, within the model.
 */
class ElectionTest {

    private fun check(model: NodeModel, persist: Persist, size: Int = 3, maxCrashes: Int = 1) =
        Election(size, model, persist, maxCrashes).check()

    @Test
    fun `a restart reloads the vote from disk and forgets everything else`() {
        val before = Node("n2", up = false, memVote = "n3", diskVote = "n1", unflushed = true, votes = setOf("n2"))
        assertThat(recover(before)).isEqualTo(Node("n2", up = true, memVote = "n1", diskVote = "n1"))
        assertThat(recover(Node("n2", up = false, memVote = "n1"))).isEqualTo(Node("n2"))
    }

    @Test
    fun `each way of storing a vote leaves the disk in a different state`() {
        val n2 = Node("n2")
        assertThat(castVote(n2, "n1", Persist.NEVER)).isEqualTo(Node("n2", memVote = "n1"))
        assertThat(castVote(n2, "n1", Persist.AFTER_REPLY)).isEqualTo(Node("n2", memVote = "n1", unflushed = true))
        assertThat(castVote(n2, "n1", Persist.BEFORE_REPLY)).isEqualTo(Node("n2", memVote = "n1", diskVote = "n1"))
    }

    @Test
    fun `without crashes every run elects exactly one leader`() {
        val result = check(NodeModel.CRASH_STOP, Persist.NEVER, maxCrashes = 0)
        assertThat(result.violation).isNull()
        assertThat(result.stuck).isZero()
    }

    @Test
    fun `under crash-stop a vote kept only in memory is safe`() {
        val result = check(NodeModel.CRASH_STOP, Persist.NEVER)
        assertThat(result.violation).isNull()
    }

    @Test
    fun `under crash-stop one crash can leave the election stuck forever`() {
        // safety holds in every state, but in some runs nobody ever wins: liveness is not guaranteed
        val result = check(NodeModel.CRASH_STOP, Persist.NEVER)
        assertThat(result.stuck).isPositive()
    }

    @Test
    fun `under crash-recovery a vote kept only in memory elects two leaders`() {
        val result = check(NodeModel.CRASH_RECOVERY, Persist.NEVER)
        assertThat(result.violation).isNotNull()
        assertThat(result.badState!!.elected).hasSize(2)
        // the shortest way: some node votes, crashes, restarts having forgotten, and votes again
        val trace = result.violation!!
        val crashed = trace.first { it.endsWith(" crashes") }.removeSuffix(" crashes")
        assertThat(trace).contains("$crashed restarts")
        assertThat(trace.size).isEqualTo(6)
    }

    @Test
    fun `replying before the vote reaches disk is as bad as never writing it`() {
        val result = check(NodeModel.CRASH_RECOVERY, Persist.AFTER_REPLY)
        assertThat(result.violation).isNotNull()
        val trace = result.violation!!
        val crash = trace.indexOfFirst { it.endsWith(" crashes") }
        val crashed = trace[crash].removeSuffix(" crashes")
        // the node that crashed never wrote its vote to disk before the crash
        assertThat(trace.subList(0, crash)).doesNotContain("$crashed writes its vote to disk")
        assertThat(trace).contains("$crashed restarts")
    }

    @Test
    fun `under crash-recovery writing the vote to disk before replying keeps one leader`() {
        val result = check(NodeModel.CRASH_RECOVERY, Persist.BEFORE_REPLY)
        assertThat(result.violation).isNull()
    }

    @Test
    fun `with five nodes and two crashes the fix still holds, over many more states`() {
        val small = check(NodeModel.CRASH_RECOVERY, Persist.BEFORE_REPLY)
        val big = check(NodeModel.CRASH_RECOVERY, Persist.BEFORE_REPLY, size = 5, maxCrashes = 2)
        assertThat(big.violation).isNull()
        assertThat(big.states).isGreaterThan(small.states * 100)
        assertThat(check(NodeModel.CRASH_RECOVERY, Persist.NEVER, size = 5).violation).isNotNull()
    }
}
