package sfz.dist.l07

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import sfz.dist.l07.Verdict.APPROVE
import sfz.dist.l07.Verdict.DECLINE

/**
 * Exercise 4: majority voting with one liar. Each test runs every round there is: each verdict the
 * leader could hold, each node as the liar, every combination of lies it could tell.
 */
class GeneralsTest {

    @Test
    fun `the majority wins and a tie follows the rule`() {
        assertThat(decide(APPROVE, listOf(APPROVE, DECLINE), Tie.DECLINE)).isEqualTo(APPROVE)
        assertThat(decide(DECLINE, listOf(APPROVE, APPROVE), Tie.DECLINE)).isEqualTo(APPROVE)
        assertThat(decide(APPROVE, listOf(DECLINE), Tie.DECLINE)).isEqualTo(DECLINE)
        assertThat(decide(APPROVE, listOf(DECLINE), Tie.APPROVE)).isEqualTo(APPROVE)
        assertThat(decide(DECLINE, listOf(APPROVE), Tie.LEADER)).isEqualTo(DECLINE)
        assertThat(decide(APPROVE, emptyList(), Tie.DECLINE)).isEqualTo(APPROVE)
    }

    @Test
    fun `with four nodes no single liar can break agreement or validity`() {
        for (tie in Tie.entries) {
            val rounds = allRounds(4, tie)
            assertThat(rounds).hasSize(40)        // 2 verdicts x (8 lies by the leader + 3 followers x 4 lies)
            assertThat(rounds.mapNotNull { broken(it) }).isEmpty()
        }
    }

    @Test
    fun `with three nodes one lying follower makes an honest one ignore an honest leader`() {
        val r = findViolation(3, Tie.DECLINE)!!
        assertThat(r.liar).isEqualTo(1)
        assertThat(r.leaderSays).isEqualTo(APPROVE)
        assertThat(r.decisions).isEqualTo(mapOf(2 to DECLINE))
        assertThat(broken(r)).startsWith("validity")
    }

    @Test
    fun `with three nodes every tie rule fails for some liar`() {
        for (tie in Tie.entries) assertThat(findViolation(3, tie)).`as`("tie rule $tie").isNotNull()
        // trusting the leader on a tie lets a lying leader split the two followers
        val split = findViolation(3, Tie.LEADER)!!
        assertThat(split.liar).isEqualTo(0)
        assertThat(split.decisions.values.toSet()).containsExactlyInAnyOrder(APPROVE, DECLINE)
    }

    @Test
    fun `with five nodes a fixed tie rule is safe and a tie rule that trusts your own view is not`() {
        assertThat(findViolation(5, Tie.DECLINE)).isNull()
        assertThat(broken(findViolation(5, Tie.LEADER)!!)).startsWith("agreement")
    }
}
