package sfz.cache.l03

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Timeout
import org.junit.jupiter.api.extension.ExtendWith
import sfz.redis.support.KeySpace
import sfz.redis.support.TestRedis
import sfz.redis.support.WithRedis
import java.util.concurrent.TimeUnit

// pins the Redis 8.10 defaults: zset/set-max-listpack-entries 128, hash-max-listpack-entries 512,
// set-max-intset-entries 512, *-max-listpack-value 64
@ExtendWith(WithRedis::class)
@Timeout(20, unit = TimeUnit.SECONDS)
class EncodingProbeTest {
    private val redis = TestRedis.jedis

    @Test
    fun `describe reads the encoding and the memory of a key`(keys: KeySpace) {
        val key = keys("auths:today")
        redis.set(key, "41")

        val snap = EncodingProbe.describe(redis, key)

        assertThat(snap.encoding()).isEqualTo("int")
        assertThat(snap.bytes()).isPositive()
    }

    @Test
    fun `a sorted set leaves listpack at its 129th member, and grows several times bigger`(keys: KeySpace) {
        val key = keys("merchants")

        val t = EncodingProbe.growUntilConverted(redis, key, 300) { i -> redis.zadd(key, i.toDouble(), "m-$i") }

        assertThat(t).isNotNull
        assertThat(t.from()).isEqualTo("listpack")
        assertThat(t.to()).isEqualTo("skiplist")
        assertThat(t.atSize()).isEqualTo(129)
        assertThat(t.bytesAfter()).isGreaterThan(5 * t.bytesBefore())
    }

    @Test
    fun `a hash leaves listpack at its 513th field`(keys: KeySpace) {
        val key = keys("payment:43")

        val t = EncodingProbe.growUntilConverted(redis, key, 600) { i -> redis.hset(key, "f$i", "v$i") }

        assertThat(t).isNotNull
        assertThat(t.from() to t.to()).isEqualTo("listpack" to "hashtable")
        assertThat(t.atSize()).isEqualTo(513)
    }

    @Test
    fun `a set of integers leaves intset at its 513th member`(keys: KeySpace) {
        val key = keys("card-ids")

        val t = EncodingProbe.growUntilConverted(redis, key, 600) { i -> redis.sadd(key, (1000 + i).toString()) }

        assertThat(t).isNotNull
        assertThat(t.from() to t.to()).isEqualTo("intset" to "hashtable")
        assertThat(t.atSize()).isEqualTo(513)
    }

    @Test
    fun `a set of strings leaves listpack at its 129th member`(keys: KeySpace) {
        val key = keys("fraud:flagged")

        val t = EncodingProbe.growUntilConverted(redis, key, 300) { i -> redis.sadd(key, "card:$i") }

        assertThat(t).isNotNull
        assertThat(t.from() to t.to()).isEqualTo("listpack" to "hashtable")
        assertThat(t.atSize()).isEqualTo(129)
    }

    @Test
    fun `one member longer than 64 bytes converts a small sorted set at once`(keys: KeySpace) {
        val key = keys("merchants")
        val longId = "m-" + "x".repeat(63)                       // 65 bytes

        val t = EncodingProbe.growUntilConverted(redis, key, 10) { i ->
            redis.zadd(key, i.toDouble(), if (i == 3) longId else "m-$i")
        }

        assertThat(t).isNotNull
        assertThat(t.from() to t.to()).isEqualTo("listpack" to "skiplist")
        assertThat(t.atSize()).isEqualTo(3)
    }

    @Test
    fun `nothing converts below the limits`(keys: KeySpace) {
        val key = keys("merchants")

        val t = EncodingProbe.growUntilConverted(redis, key, 100) { i -> redis.zadd(key, i.toDouble(), "m-$i") }

        assertThat(t).isNull()
        assertThat(EncodingProbe.describe(redis, key).encoding()).isEqualTo("listpack")
    }

    @Test
    fun `shrinking a sorted set does not convert it back`(keys: KeySpace) {
        val key = keys("merchants")
        EncodingProbe.growUntilConverted(redis, key, 300) { i -> redis.zadd(key, i.toDouble(), "m-$i") }

        redis.zremrangeByRank(key, 0, 119)                       // 129 members down to 9

        assertThat(redis.zcard(key)).isEqualTo(9)
        assertThat(EncodingProbe.describe(redis, key).encoding()).isEqualTo("skiplist")
    }
}
