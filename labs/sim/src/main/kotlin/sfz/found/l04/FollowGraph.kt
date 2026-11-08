package sfz.found.l04

import kotlin.math.pow
import kotlin.random.Random

// Finished: read it, don't change it. The same file is in src/solution.

/**
 * Who follows whom. Users are numbered `0 until size`.
 * `followers(u)` are the users who see u's posts; `followees(u)` are the accounts u follows.
 */
class FollowGraph private constructor(
    val size: Int,
    private val followersOf: Array<IntArray>,
    private val followeesOf: Array<IntArray>,
) {
    fun followers(user: Int): IntArray = followersOf[user]
    fun followees(user: Int): IntArray = followeesOf[user]
    fun followerCount(user: Int): Int = followersOf[user].size
    fun followeeCount(user: Int): Int = followeesOf[user].size

    /** Total number of follow edges. */
    val edges: Long get() = followeesOf.sumOf { it.size.toLong() }

    companion object {
        /** Builds a graph from `follower to followee` pairs, for example `of(3, 1 to 0, 2 to 0)`. */
        fun of(size: Int, vararg follows: Pair<Int, Int>): FollowGraph = build(size, follows.asList())

        /**
         * A skewed graph like a real social network. User 0 is the most popular account, user 1 the
         * next, and so on: each ordinary user follows [followsPerUser] accounts picked with weight
         * 1 / (rank + 1)^[exponent], so a few accounts collect most of the follows. The last
         * [heavyUsers] users follow [heavyFollows] accounts each (bots, news junkies, the users who
         * follow everyone back). Same seed, same graph.
         */
        fun skewed(
            size: Int,
            followsPerUser: Int = 50,
            heavyUsers: Int = 20,
            heavyFollows: Int = 4_000,
            exponent: Double = 0.8,
            seed: Long = 42,
        ): FollowGraph {
            require(heavyFollows < size && followsPerUser < size)
            val cdf = DoubleArray(size)
            var total = 0.0
            for (i in 0 until size) {
                total += 1.0 / (i + 1.0).pow(exponent)
                cdf[i] = total
            }
            val random = Random(seed)
            val pairs = ArrayList<Pair<Int, Int>>(size * followsPerUser + heavyUsers * heavyFollows)
            for (user in 0 until size) {
                val want = if (user >= size - heavyUsers) heavyFollows else followsPerUser
                val picked = HashSet<Int>(want * 2)
                while (picked.size < want) {
                    var target = cdf.binarySearch(random.nextDouble() * total)
                    if (target < 0) target = -target - 1
                    if (target != user) picked += target.coerceAtMost(size - 1)
                }
                for (followee in picked) pairs += user to followee
            }
            return build(size, pairs)
        }

        private fun build(size: Int, follows: List<Pair<Int, Int>>): FollowGraph {
            val outCount = IntArray(size)
            val inCount = IntArray(size)
            for ((follower, followee) in follows) {
                require(follower != followee) { "user $follower can't follow itself" }
                outCount[follower]++
                inCount[followee]++
            }
            val followees = Array(size) { IntArray(outCount[it]) }
            val followers = Array(size) { IntArray(inCount[it]) }
            val o = IntArray(size)
            val i = IntArray(size)
            for ((follower, followee) in follows) {
                followees[follower][o[follower]++] = followee
                followers[followee][i[followee]++] = follower
            }
            return FollowGraph(size, followers, followees)
        }
    }
}
