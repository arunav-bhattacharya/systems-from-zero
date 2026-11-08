package sfz.repl.l02

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import net.jqwik.api.constraints.LongRange
import org.assertj.core.api.Assertions.assertThat
import kotlin.random.Random

/**
 * Property tests over random workloads: inserts with now() and random(), relative fee updates,
 * deletes with LIMIT and inserts that commit out of order, on followers with any clock lag.
 */
class ReplayPropertyTest {
    private fun workload(seed: Long, size: Int, withDeletes: Boolean): List<Statement> {
        val r = Random(seed)
        val merchants = listOf("m1", "m2", "m3")
        return List(size) {
            when (r.nextInt(if (withDeletes) 10 else 8)) {
                in 0..5 -> Statement.Insert(merchants.random(r), r.nextLong(100, 50_000))
                6, 7 -> Statement.AddFee(merchants.random(r), r.nextLong(1, 100))
                else -> Statement.DeleteSome(merchants.random(r).takeIf { r.nextBoolean() }, r.nextInt(1, 3))
            }
        }
    }

    @Property(tries = 100)
    fun `a row replica always ends up with the leader's table`(
        @ForAll seed: Long,
        @ForAll @IntRange(min = 1, max = 60) size: Int,
        @ForAll @LongRange(min = 0, max = 5_000) lagMs: Long,
    ) {
        val p = TwoServers(lagMs)
        workload(seed, size, withDeletes = true).forEachIndexed { i, s ->
            if (i % 7 == 3 && s is Statement.Insert) p.leader.runInterleaved(s, Statement.Insert("m9", 1)) else p.run(s)
        }
        p.follower.replayRows(p.leader.rowLog)
        assertThat(p.follower.rows).isEqualTo(p.leader.rows)
    }

    @Property(tries = 100)
    fun `with pinned values a statement replica matches when no statement depends on scan or commit order`(
        @ForAll seed: Long,
        @ForAll @IntRange(min = 1, max = 60) size: Int,
        @ForAll @LongRange(min = 1, max = 5_000) lagMs: Long,
    ) {
        val pinned = TwoServers(lagMs).apply { leader.pinValues = true }
        val unpinned = TwoServers(lagMs)
        val statements = workload(seed, size, withDeletes = false)
        statements.forEach { pinned.run(it); unpinned.run(it) }
        pinned.follower.replayStatements(pinned.leader.statementLog)
        unpinned.follower.replayStatements(unpinned.leader.statementLog)

        assertThat(pinned.follower.rows).isEqualTo(pinned.leader.rows)
        if (statements.any { it is Statement.Insert }) assertThat(unpinned.follower.rows).isNotEqualTo(unpinned.leader.rows)
    }
}
