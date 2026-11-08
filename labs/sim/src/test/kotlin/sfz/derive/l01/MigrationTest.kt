package sfz.derive.l01

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

/** Kreps's recipe, step by step: replay into a new table, shift readers, roll back, retire. */
class MigrationTest {
    private val world = World(seed = 2026)
    private val migration = Migration(world.log, world.v1)

    @Test
    fun `v2 replays from offset 0 into its own table while v1 serves every read`() {
        val v2 = migration.startV2(DailyNet(), batch = 400)
        assertThat(v2.position).isEqualTo(0)
        assertThat(v2.view).isNotSameAs(world.v1.view)

        repeat(3) { world.tick(migration) }

        assertThat(v2.position).isEqualTo(1_200)                  // three polls of 400, from the start
        assertThat(world.v1.lag).isEqualTo(0)                     // v1 keeps up with live traffic
        for (m in MERCHANTS) assertThat(migration.read(m, world.today - 1).version).isEqualTo("v1")
    }

    @Test
    fun `starting v2 twice is a mistake`() {
        migration.startV2(DailyNet(), batch = 400)
        assertThrows<IllegalStateException> { migration.startV2(DailyNet(), batch = 400) }
    }

    @Test
    fun `shift is refused while v2 is behind and accepted on the tick its lag reaches zero`() {
        assertThat(migration.shift(10)).isFalse()                 // no v2 yet
        migration.startV2(DailyNet(), batch = 400)
        val history = world.log.end                               // 30 days x 200 payments
        assertThat(history).isEqualTo(6_000)

        var ticks = 0
        while (true) {
            world.tick(migration, live = 5)
            ticks++
            if (migration.v2!!.lag == 0L) break
            assertThat(migration.shift(10)).isFalse()
            assertThat(migration.percentOnV2).isZero()
        }
        // each minute v2 reads 400 and the log grows by 5: it gains 395 a minute on 6,000
        assertThat(ticks).isEqualTo(((history + 394) / 395).toInt())
        assertThat(migration.shift(10)).isTrue()
        assertThat(migration.percentOnV2).isEqualTo(10)
    }

    @Test
    fun `each merchant reads one version, and the share on v2 follows the percentage`() {
        migration.startV2(DailyNet(), batch = 400)
        Truth.catchUp(world, migration)

        assertThat(migration.shift(30)).isTrue()
        val onV2 = MERCHANTS.filter { bucketOf(it) < 30 }
        assertThat(onV2).isNotEmpty().hasSizeLessThan(MERCHANTS.size)
        for (m in MERCHANTS) {
            val want = if (m in onV2) "v2" else "v1"
            repeat(3) { assertThat(migration.read(m, world.today).version).isEqualTo(want) }
        }

        assertThat(migration.shift(100)).isTrue()
        for (m in MERCHANTS) assertThat(migration.read(m, world.today).version).isEqualTo("v2")
    }

    @Test
    fun `rollback sends every reader back to a v1 that kept up`() {
        migration.startV2(DailyNet(), batch = 400)
        Truth.catchUp(world, migration)
        assertThat(migration.shift(100)).isTrue()
        repeat(30) { world.tick(migration) }                      // half an hour on v2

        migration.rollback()

        assertThat(migration.percentOnV2).isZero()
        val v1Truth = Truth.grossByArrivalDay(world)
        for (m in MERCHANTS) {
            val a = migration.read(m, world.today)
            assertThat(a.version).isEqualTo("v1")
            assertThat(a.cents).isEqualTo(v1Truth[m to world.today] ?: 0)   // includes the last half hour
        }
    }

    @Test
    fun `v1 can be retired only at 100 percent, and then there is no way back`() {
        migration.startV2(DailyNet(), batch = 400)
        Truth.catchUp(world, migration)
        assertThat(migration.shift(50)).isTrue()
        assertThrows<IllegalStateException> { migration.retireV1() }

        assertThat(migration.shift(100)).isTrue()
        migration.retireV1()

        assertThat(migration.v1Retired).isTrue()
        assertThat(world.v1.running).isFalse()
        assertThat(world.v1.view.cents("m-01", world.today - 1)).isZero()  // its table is gone
        assertThrows<IllegalStateException> { migration.rollback() }
        world.tick(migration)                                     // v2 carries on alone
        assertThat(migration.v2!!.lag).isZero()
    }
}
