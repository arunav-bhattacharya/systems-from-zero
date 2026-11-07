package sfz.redis.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.util.concurrent.TimeUnit

@ExtendWith(WithRedis::class)
@Timeout(10, unit = TimeUnit.SECONDS)
class LeaderboardTest {
    private val redis = TestRedis.jedis

    /** m-01 has 10 approvals, m-02 has 20, ... m-10 has 100. */
    private fun tenMerchants(keys: KeySpace): Leaderboard {
        val board = Leaderboard(redis, keys("merchants:approved"))
        for (i in 1..10) board.record("m-%02d".format(i), i * 10L)
        return board
    }

    @Test
    fun `record adds up approvals and reversals and returns the new total`(keys: KeySpace) {
        val board = Leaderboard(redis, keys("merchants:approved"))

        assertThat(board.record("m-17")).isEqualTo(1)
        assertThat(board.record("m-17")).isEqualTo(2)
        assertThat(board.record("m-17", 5)).isEqualTo(7)
        assertThat(board.record("m-17", -3)).isEqualTo(4)
        assertThat(redis.zscore(keys("merchants:approved"), "m-17")).isEqualTo(4.0)
    }

    @Test
    fun `top lists the highest totals first with ranks starting at 1`(keys: KeySpace) {
        val board = tenMerchants(keys)

        assertThat(board.top(3)).containsExactly(
            Standing("m-10", 100, 1),
            Standing("m-09", 90, 2),
            Standing("m-08", 80, 3),
        )
        assertThat(board.top(50)).hasSize(10)
    }

    @Test
    fun `equal totals come out in reverse member order`(keys: KeySpace) {
        val board = Leaderboard(redis, keys("merchants:approved"))
        board.record("m-anna", 5)
        board.record("m-bert", 5)
        board.record("m-cora", 7)
        board.record("m-dave", 3)

        // under REV, Redis orders equal scores by member in descending byte order
        assertThat(board.top(4).map { it.merchant }).containsExactly("m-cora", "m-bert", "m-anna", "m-dave")
        assertThat(board.standingOf("m-anna")).isEqualTo(Standing("m-anna", 5, 3))
    }

    @Test
    fun `standingOf gives rank and total, or null for a merchant with no entry`(keys: KeySpace) {
        val board = tenMerchants(keys)

        assertThat(board.standingOf("m-10")).isEqualTo(Standing("m-10", 100, 1))
        assertThat(board.standingOf("m-01")).isEqualTo(Standing("m-01", 10, 10))
        assertThat(board.standingOf("m-99")).isNull()
    }

    @Test
    fun `a reversal moves a merchant down the board`(keys: KeySpace) {
        val board = tenMerchants(keys)

        board.record("m-10", -95)                       // 100 approvals, 95 reversed

        assertThat(board.standingOf("m-10")).isEqualTo(Standing("m-10", 5, 10))
        assertThat(board.top(1).single().merchant).isEqualTo("m-09")
    }

    @Test
    fun `around shows the neighbours on both sides and is cut short at the top`(keys: KeySpace) {
        val board = tenMerchants(keys)

        assertThat(board.around("m-05", 2).map { it.rank }).containsExactly(4L, 5L, 6L, 7L, 8L)
        assertThat(board.around("m-05", 2).map { it.merchant }).containsExactly("m-07", "m-06", "m-05", "m-04", "m-03")
        assertThat(board.around("m-10", 2).map { it.merchant }).containsExactly("m-10", "m-09", "m-08")
        assertThat(board.around("m-01", 1).map { it.rank }).containsExactly(9L, 10L)
        assertThat(board.around("m-99", 2)).isEmpty()
    }
}
