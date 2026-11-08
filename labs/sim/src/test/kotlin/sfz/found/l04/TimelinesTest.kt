package sfz.found.l04

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.within
import org.junit.jupiter.api.Test
import kotlin.random.Random

class TimelinesTest {
    // Ana (0) is followed by Ben (1), Cleo (2) and Dev (3). Ben is followed by Cleo.
    private val tiny = FollowGraph.of(4, 1 to 0, 2 to 0, 3 to 0, 2 to 1)

    @Test
    fun `fan-out on write costs one write per follower and one lookup per read`() {
        val t = FanOutOnWrite(tiny)
        t.post(0, 1)                                        // Ana: 3 followers
        t.post(1, 2)                                        // Ben: 1 follower
        assertThat(t.work.writes).isEqualTo(4)
        assertThat(t.homeTimeline(2, 10)).containsExactly(2L, 1L)
        assertThat(t.homeTimeline(1, 10)).containsExactly(1L)
        assertThat(t.homeTimeline(0, 10)).isEmpty()
        assertThat(t.work.lookups).isEqualTo(3)
    }

    @Test
    fun `fan-out on write keeps only the newest cap posts`() {
        val t = FanOutOnWrite(tiny, cap = 3)
        for (id in 1L..5L) t.post(0, id)
        assertThat(t.homeTimeline(1, 10)).containsExactly(5L, 4L, 3L)
        assertThat(t.homeTimeline(1, 2)).containsExactly(5L, 4L)
        assertThat(t.work.writes).isEqualTo(15)            // 5 posts x 3 followers, trimming is free
    }

    @Test
    fun `the loss factor keeps every write up to the limit and shrinks above it`() {
        assertThat(lossFactor(200)).isEqualTo(1.0)
        assertThat(lossFactor(2_000)).isEqualTo(1.0)
        assertThat(lossFactor(4_000)).isEqualTo(0.5)
        assertThat(lossFactor(8_000)).isEqualTo(0.25)
        assertThat(lossFactor(0)).isEqualTo(1.0)
        assertThat(lossFactor(300, reasonableLimit = 100)).isCloseTo(1.0 / 3, within(1e-12))
    }

    @Test
    fun `the hybrid stores a celebrity post once and merges it when a follower reads`() {
        val t = Hybrid(tiny, celebrityFollowers = 2)       // Ana has 3 followers, so she is a celebrity
        t.post(0, 1)                                        // stored once: 1 write
        t.post(1, 2)                                        // Ben is fanned out to Cleo: 1 write
        assertThat(t.work.writes).isEqualTo(2)
        assertThat(t.homeTimeline(2, 10)).containsExactly(2L, 1L)   // her timeline + Ana's list
        assertThat(t.work.lookups).isEqualTo(2)
        assertThat(t.homeTimeline(1, 10)).containsExactly(1L)       // empty timeline + Ana's list
        assertThat(t.work.lookups).isEqualTo(4)
        assertThat(t.homeTimeline(0, 10)).isEmpty()                 // Ana follows nobody: 1 lookup
        assertThat(t.work.lookups).isEqualTo(5)
    }

    @Test
    fun `a heavy follower gets about the share of writes the loss factor allows`() {
        val size = 8_001                                    // user 0 follows the other 8,000 users
        val graph = FollowGraph.of(size, *Array(size - 1) { 0 to it + 1 })
        val t = Hybrid(graph, celebrityFollowers = 1_000, cap = 10_000)
        for (author in 1 until size) t.post(author, author.toLong())
        val kept = t.homeTimeline(0, 10_000).size
        assertThat(kept / 8_000.0).isCloseTo(0.25, within(0.03))     // min(2000 / 8000, 1)
        assertThat(t.work.writes).isEqualTo(kept.toLong())             // a dropped write costs nothing
    }

    @Test
    fun `on a skewed graph the hybrid caps the writes per post and keeps reads cheap`() {
        val graph = FollowGraph.skewed(20_000, seed = 7)
        val threshold = 2_000
        val pull = FanOutOnRead(graph)
        val push = FanOutOnWrite(graph)
        val hybrid = Hybrid(graph, threshold)
        var worstPush = 0L
        var worstHybrid = 0L
        for (user in 0 until graph.size) {                  // everyone posts once
            val id = user.toLong()
            pull.post(user, id)
            worstPush = maxOf(worstPush, cost(push) { push.post(user, id) })
            worstHybrid = maxOf(worstHybrid, cost(hybrid) { hybrid.post(user, id) })
        }
        for (user in 0 until graph.size) {                  // then everyone reads once
            pull.homeTimeline(user, 50); push.homeTimeline(user, 50); hybrid.homeTimeline(user, 50)
        }
        val n = graph.size.toDouble()
        assertThat(pull.work.writes).isEqualTo(graph.size.toLong())
        assertThat(pull.work.lookups).isEqualTo(graph.edges)            // every follow, once per read
        assertThat(push.work.writes).isEqualTo(graph.edges)             // every follow, once per post
        assertThat(push.work.lookups).isEqualTo(graph.size.toLong())
        assertThat(worstPush).isEqualTo((0 until graph.size).maxOf { graph.followerCount(it) }.toLong())
        assertThat(worstHybrid).isLessThanOrEqualTo(threshold.toLong())
        val celebrities = (0 until graph.size).filter { graph.followerCount(it) > threshold }
        val celebrityFollows = celebrities.sumOf { graph.followerCount(it).toLong() }
        // each celebrity post is one write instead of one per follower; sampling only removes more
        assertThat(hybrid.work.writes).isLessThanOrEqualTo(push.work.writes - celebrityFollows + celebrities.size)
        // a hybrid read: one timeline, plus one list per celebrity followed
        assertThat(hybrid.work.lookups).isEqualTo(graph.size + celebrityFollows)
        assertThat(hybrid.work.lookups / n).isLessThan(pull.work.lookups / n / 4)
    }

    private fun cost(t: Timelines, action: () -> Unit): Long {
        val before = t.work.writes
        action()
        return t.work.writes - before
    }

    @Test
    fun `one queue delivers in arrival order, so a celebrity post delays the posts behind it`() {
        val posts = listOf(
            QueuedPost(0.0, 1_000_000),                     // a celebrity: 10 s of writes
            QueuedPost(1.0, 200),                           // arrives while the celebrity is fanning out
            QueuedPost(20.0, 200),                          // arrives to an empty queue
        )
        val d = deliverySeconds(posts, writesPerSecond = 100_000.0)
        assertThat(d).hasSize(3)
        assertThat(d[0]).isCloseTo(10.0, within(1e-9))
        assertThat(d[1]).isCloseTo(9.002, within(1e-9))   // waits 9 s, then 2 ms of its own
        assertThat(d[2]).isCloseTo(0.002, within(1e-9))
    }

    @Test
    fun `the celebrity threshold is throughput times the deadline`() {
        assertThat(celebrityThreshold(300_000.0, 5.0)).isEqualTo(1_500_000)
        assertThat(celebrityThreshold(1_000.0, 2.5)).isEqualTo(2_500)
        assertThat(celebrityThreshold(1_500.0, 0.999)).isEqualTo(1_498)
    }
}

class SameTimelinesProperties {
    @Property(tries = 80)
    fun `every design shows every user the same home timeline`(@ForAll seed: Long) {
        val random = Random(seed)
        val size = random.nextInt(2, 40)
        val follows = ArrayList<Pair<Int, Int>>()
        for (a in 0 until size) for (b in 0 until size) if (a != b && random.nextDouble() < 0.2) follows += a to b
        val graph = FollowGraph.of(size, *follows.toTypedArray())
        val designs = listOf(
            FanOutOnRead(graph),
            FanOutOnWrite(graph, cap = 30),
            Hybrid(graph, celebrityFollowers = random.nextInt(0, 8), cap = 30),
        )
        repeat(random.nextInt(0, 300)) { id ->
            val author = random.nextInt(size)
            for (d in designs) d.post(author, id.toLong())
        }
        for (user in 0 until size) {
            val expected = designs[0].homeTimeline(user, 20)
            for (d in designs.drop(1)) {
                assertThat(d.homeTimeline(user, 20)).describedAs("${d::class.simpleName}, user $user").isEqualTo(expected)
            }
        }
    }
}
