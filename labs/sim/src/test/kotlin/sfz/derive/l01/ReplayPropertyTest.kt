package sfz.derive.l01

import net.jqwik.api.ForAll
import net.jqwik.api.Property
import net.jqwik.api.constraints.IntRange
import org.assertj.core.api.Assertions.assertThat

/**
 * A property test: jqwik picks many seeds and replay batch sizes and reports the smallest case
 * that breaks. The property is what makes reprocessing safe: the replayed table doesn't depend on
 * how the replay was chunked or how long it took, only on the log.
 */
class ReplayPropertyTest {
    @Property(tries = 30)
    fun `for any seed and replay batch size, the caught-up v2 is the batch answer`(
        @ForAll seed: Long,
        @ForAll @IntRange(min = 20, max = 3_000) batch: Int,
    ) {
        val world = World(seed, days = 10, perDay = 100)
        val migration = Migration(world.log, world.v1)
        val v2 = migration.startV2(DailyNet(), batch)
        Truth.catchUp(world, migration, live = 5)

        val truth = Truth.netByEventDay(world.log)
        for (m in MERCHANTS) for (day in 0..world.today) {
            assertThat(v2.view.cents(m, day)).isEqualTo(truth[m to day] ?: 0)
        }
    }
}
