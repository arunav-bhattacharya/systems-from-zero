package sfz.dist.l07

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.Test

/**
 * Exercise 1 on small models you can check by hand. Two threads each add 1 to a shared counter x.
 * In [Racy] an increment is two steps (read x into a register, then write register + 1); in
 * [Atomic] it is one step. The rule: once both threads are done, x == 2.
 */
class ExplorerTest {

    /** pc is each thread's next step: 0 read, 1 write, 2 done. r is each thread's register. */
    data class Racy(val x: Int = 0, val pc: List<Int> = listOf(0, 0), val r: List<Int> = listOf(0, 0))

    private fun racySteps(s: Racy): List<Pair<String, Racy>> = (0..1).mapNotNull { t ->
        val name = "T${t + 1}"
        when (s.pc[t]) {
            0 -> "$name reads x=${s.x}" to s.copy(pc = s.pc.set(t, 1), r = s.r.set(t, s.x))
            1 -> "$name writes x=${s.r[t] + 1}" to s.copy(x = s.r[t] + 1, pc = s.pc.set(t, 2))
            else -> null
        }
    }

    private fun bothDoneMeansTwo(s: Racy) = s.pc != listOf(2, 2) || s.x == 2

    data class Atomic(val x: Int = 0, val done: List<Boolean> = listOf(false, false))

    private fun atomicSteps(s: Atomic): List<Pair<String, Atomic>> = (0..1).mapNotNull { t ->
        if (s.done[t]) null else "T${t + 1} adds 1" to Atomic(s.x + 1, s.done.set(t, true))
    }

    private fun <T> List<T>.set(i: Int, v: T): List<T> = toMutableList().also { it[i] = v }

    @Test
    fun `it finds the lost update and returns a shortest trace`() {
        val result = explore(Racy(), ::racySteps, ::bothDoneMeansTwo)
        assertThat(result.violation).containsExactly("T1 reads x=0", "T2 reads x=0", "T1 writes x=1", "T2 writes x=1")
        assertThat(result.badState).isEqualTo(Racy(x = 1, pc = listOf(2, 2), r = listOf(0, 0)))
    }

    @Test
    fun `a state reached by two paths is counted once`() {
        // start; T1 done; T2 done; both done (reached from either side, x == 2)
        val result = explore(Atomic(), ::atomicSteps, { s -> !s.done.all { it } || s.x == 2 })
        assertThat(result.violation).isNull()
        assertThat(result.badState).isNull()
        assertThat(result.states).isEqualTo(4)
    }

    @Test
    fun `when nothing breaks it visits every reachable state`() {
        // the racy model with a rule that always holds: 1 + 2 + 3 + 4 + 3 = 13 states, by hand
        val result = explore(Racy(), ::racySteps, { true })
        assertThat(result.violation).isNull()
        assertThat(result.states).isEqualTo(13)
    }

    @Test
    fun `a model with a loop still ends`() {
        // a clock that ticks 0, 1, 2, 0, 1, 2... forever has three states
        val result = explore(0, { s -> listOf("tick" to (s + 1) % 3) }, { true })
        assertThat(result.states).isEqualTo(3)
        assertThat(result.stuck).isZero()
    }

    @Test
    fun `states with no way forward that are not done count as stuck`() {
        // 0 -> 1 -> 2 and 0 -> 3; only 2 is done, so 3 is stuck
        val edges = mapOf(0 to listOf(1, 3), 1 to listOf(2))
        val result = explore(0, { s -> edges[s].orEmpty().map { "to $it" to it } }, { true }, done = { it == 2 })
        assertThat(result.states).isEqualTo(4)
        assertThat(result.stuck).isEqualTo(1)
    }

    @Test
    fun `it gives up past the limit instead of running out of memory`() {
        assertThatThrownBy { explore(0, { s -> listOf("up" to s + 1) }, { true }, limit = 1_000) }
            .isInstanceOf(TooManyStates::class.java)
    }
}
