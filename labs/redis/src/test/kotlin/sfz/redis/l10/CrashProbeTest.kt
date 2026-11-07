package sfz.redis.l10

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.Assertions.assertThatThrownBy
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import sfz.redis.support.CrashRedis
import java.util.concurrent.TimeUnit

// talks to a separate Redis 8.10 container whose server process the tests kill -9 (Docker);
// each test writes a fresh redis.conf and starts the server from an empty /data first
@Timeout(60, unit = TimeUnit.SECONDS)
class CrashProbeTest {
    private val redis = CrashRedis.jedis
    private val probe = CrashProbe(redis, CrashRedis::crash)

    companion object {
        @JvmStatic
        @BeforeAll
        fun startServer() {
            CrashRedis.restartWith(CrashRedis.NO_PERSISTENCE)
        }
    }

    @Test
    fun `write sets every payment and count finds them`() {
        CrashRedis.restartWith(CrashRedis.NO_PERSISTENCE)

        probe.write("pay:", 0, 50)

        assertThat(redis.get("pay:0")).isEqualTo("settled")
        assertThat(redis.get("pay:49")).isEqualTo("settled")
        assertThat(redis.exists("pay:50")).isFalse()
        assertThat(probe.count("pay:", 0, 50)).isEqualTo(50)
        assertThat(probe.count("pay:", 40, 60)).isEqualTo(10)
    }

    @Test
    fun `persistenceStat reads numbers from INFO persistence`() {
        CrashRedis.restartWith(CrashRedis.aof("everysec"))

        assertThat(probe.persistenceStat("aof_enabled")).isEqualTo(1)
        assertThat(probe.persistenceStat("rdb_bgsave_in_progress")).isZero()
        assertThatThrownBy { probe.persistenceStat("no_such_field") }.isInstanceOf(IllegalArgumentException::class.java)
    }

    @Test
    fun `with no persistence a crash loses every acknowledged write`() {
        CrashRedis.restartWith(CrashRedis.NO_PERSISTENCE)

        val loss = probe.writeThenCrash("pay:", 300)

        assertThat(loss).isEqualTo(CrashProbe.Loss(300, 0))
        assertThat(loss.lost()).isEqualTo(300)
    }

    @Test
    fun `snapshot returns once the file is on disk`() {
        CrashRedis.restartWith(CrashRedis.NO_PERSISTENCE)
        probe.write("pay:", 0, 200)
        assertThat(probe.persistenceStat("rdb_changes_since_last_save")).isEqualTo(200)

        probe.snapshot()

        assertThat(probe.persistenceStat("rdb_bgsave_in_progress")).isZero()
        assertThat(probe.persistenceStat("rdb_changes_since_last_save")).isZero()
    }

    @Test
    fun `a snapshot keeps what came before it and loses what came after`() {
        CrashRedis.restartWith(CrashRedis.NO_PERSISTENCE)          // no save points: the only snapshot is ours
        probe.write("pay:", 0, 200)
        probe.snapshot()
        probe.write("pay:", 200, 300)                               // acknowledged, but only in memory

        CrashRedis.crash()

        assertThat(probe.count("pay:", 0, 200)).isEqualTo(200)      // loaded from dump.rdb
        assertThat(probe.count("pay:", 200, 300)).isZero()          // everything after the fork is gone
    }

    @Test
    fun `appendfsync always loses nothing that was acknowledged`() {
        CrashRedis.restartWith(CrashRedis.aof("always"))

        assertThat(probe.writeThenCrash("pay:", 300)).isEqualTo(CrashProbe.Loss(300, 300))
    }

    @Test
    fun `appendfsync everysec loses nothing when only the process dies`() {
        CrashRedis.restartWith(CrashRedis.aof("everysec"))

        // Redis write()s the log before it replies, so the kernel holds every acknowledged write in its
        // page cache; kill -9 can't take that away. Only a crash of the machine loses the last second.
        assertThat(probe.writeThenCrash("pay:", 300)).isEqualTo(CrashProbe.Loss(300, 300))
    }

    @Test
    fun `appendfsync no loses nothing when only the process dies either`() {
        CrashRedis.restartWith(CrashRedis.aof("no"))

        assertThat(probe.writeThenCrash("pay:", 300)).isEqualTo(CrashProbe.Loss(300, 300))
    }
}
