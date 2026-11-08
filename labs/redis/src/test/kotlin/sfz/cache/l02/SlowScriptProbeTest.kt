package sfz.cache.l02

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.util.concurrent.TimeUnit

// talks to the real Redis 8.10 container (Docker)
@ExtendWith(WithRedis::class)
class SlowScriptProbeTest {

    @Test
    @Timeout(10, unit = TimeUnit.SECONDS)
    fun `a GET on an idle server answers in milliseconds`(keys: KeySpace) {
        val key = keys("payment:42")
        TestRedis.jedis.set(key, "approved")
        TestRedis.newJedis().use { app ->
            app.ping()                                    // open the connection before timing

            val timing = SlowScriptProbe.timeGet(app, key)

            assertThat(timing.value()).isEqualTo("approved")
            assertThat(timing.millis()).isLessThan(200)
        }
    }

    @Test
    @Timeout(20, unit = TimeUnit.SECONDS)
    fun `a GET on another connection waits for a running script`(keys: KeySpace) {
        val key = keys("payment:42")
        TestRedis.jedis.set(key, "approved")
        TestRedis.newJedis().use { scripts ->
            TestRedis.newJedis().use { app ->
                scripts.ping(); app.ping()

                val timing = SlowScriptProbe.timeGetDuringScript(scripts, app, key, 1_500)

                // the script had about 1,300 ms left when the GET arrived; the GET waited for all of it
                assertThat(timing.value()).isEqualTo("approved")
                assertThat(timing.millis()).isBetween(1_000L, 4_000L)
            }
        }
    }

    @Test
    @Timeout(20, unit = TimeUnit.SECONDS)
    fun `a longer script makes the GET wait longer`(keys: KeySpace) {
        val key = keys("payment:42")
        TestRedis.jedis.set(key, "approved")
        TestRedis.newJedis().use { scripts ->
            TestRedis.newJedis().use { app ->
                scripts.ping(); app.ping()

                val short = SlowScriptProbe.timeGetDuringScript(scripts, app, key, 600)
                val long = SlowScriptProbe.timeGetDuringScript(scripts, app, key, 1_600)

                // one extra second of script is one extra second of waiting for an unrelated GET
                assertThat(long.millis() - short.millis()).isBetween(600L, 1_600L)
            }
        }
    }
}
