package sfz.repl.l03

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import net.jqwik.api.constraints.LongRange
import org.assertj.core.api.Assertions.assertThat
import kotlin.random.Random

/**
 * Property test: whatever the lags, the pauses and the order of writes and reads, a session routed by
 * [monotonicReads] never reads below its own last write and never goes back in time.
 */
class SessionPropertyTest {
    @Property(tries = 200)
    fun `a session with a token never misses its own write and never moves backwards`(
        @ForAll seed: Long,
        @ForAll @LongRange(min = 0, max = 1_000) lag1: Long,
        @ForAll @LongRange(min = 0, max = 1_000) lag2: Long,
        @ForAll @LongRange(min = 0, max = 1_000) lag3: Long,
        @ForAll @IntRange(min = 1, max = 80) steps: Int,
    ) {
        val r = Random(seed)
        val leader = Leader()
        val replicas = listOf(lag1, lag2, lag3).mapIndexed { i, lag -> Replica("r$i", lag, leader) }
        val client = Client(leader)
        val me = Session("me")
        val others = Session("others")
        var now = 0L
        var lastPosition = 0L
        repeat(steps) {
            now += r.nextLong(0, 200)
            when (r.nextInt(6)) {
                0 -> client.write(me, now, "k${r.nextInt(5)}", "mine-$now")
                1 -> client.write(others, now, "k${r.nextInt(5)}", "theirs-$now")
                2 -> replicas.random(r).let { if (r.nextBoolean()) it.pause(now) else it.resume() }
                else -> {
                    val read = client.read(me, now, "k0", monotonicReads(me, replicas, leader, now))
                    assertThat(read.position).isGreaterThanOrEqualTo(me.lastWritten).isGreaterThanOrEqualTo(lastPosition)
                    lastPosition = read.position
                }
            }
        }
    }
}
