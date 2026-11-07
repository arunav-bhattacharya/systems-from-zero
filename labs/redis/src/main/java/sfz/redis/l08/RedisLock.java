package sfz.redis.l08;

import redis.clients.jedis.RedisClient;

import java.time.Duration;
import java.util.Optional;

/**
 * A lock on one Redis server, with a lease (it expires on its own), an owner token and a fencing token.
 *
 * <p>For resource {@code settle} there are two keys. {@link #lockKey} holds the current holder's random token, with a
 * TTL of the lease. {@link #fenceKey} is a counter with no TTL: every successful acquire increments it, so each holder
 * gets a number larger than every holder before it. The braces put both keys in one Redis Cluster slot (lesson 11).
 */
public final class RedisLock {

    /** What a successful acquire hands back. Pass it to {@link #release} and {@link #extend}. */
    public record Lease(String resource, String token, long fence) {}

    /**
     * KEYS[1] the lock key, KEYS[2] the fence counter. ARGV[1] the token, ARGV[2] the lease in ms. Write it so that it
     * runs {@code SET KEYS[1] ARGV[1] NX PX ARGV[2]} and, only if that set the key, returns
     * {@code INCR KEYS[2]}. Otherwise it returns 0. In Lua, {@code redis.call('SET', ...)} returns {@code false} when
     * NX refused, and a table (which counts as true) when it set the key.
     */
    public static final String ACQUIRE = "return redis.error_reply('TODO: write the acquire script')";

    /**
     * KEYS[1] the lock key, ARGV[1] the token. Compare-and-delete: if {@code GET KEYS[1]} equals ARGV[1], DEL the
     * key and return 1, otherwise return 0. (On Redis 8.4+ the single command {@code DELEX key IFEQ token} does the
     * same; the script works on any version.)
     */
    public static final String RELEASE = "return redis.error_reply('TODO: write the release script')";

    private final RedisClient redis;
    private final String prefix;

    public RedisLock(RedisClient redis, String prefix) {
        this.redis = redis;
        this.prefix = prefix;
    }

    public String lockKey(String resource) {
        return prefix + "lock:{" + resource + "}";
    }

    public String fenceKey(String resource) {
        return prefix + "fence:{" + resource + "}";
    }

    /**
     * Tries once, without waiting. Makes a new random token ({@code UUID.randomUUID().toString()}), runs
     * {@link #ACQUIRE} with {@code redis.eval(ACQUIRE, keys, args)}, and returns a {@link Lease} carrying the token and
     * the fence the script returned, or empty if someone else holds the lock.
     */
    public Optional<Lease> tryAcquire(String resource, Duration lease) {
        throw new UnsupportedOperationException("TODO: run ACQUIRE: SET NX PX, then INCR the fence");
    }

    /**
     * Releases the lock if this lease still owns it, and returns true if it deleted the key.
     *
     * <p>The code below is the bug from the lesson: it deletes whatever lock is there. If this lease expired and
     * another client acquired the lock since, it deletes THEIR lock. Replace it with {@link #RELEASE}.
     */
    public boolean release(Lease lease) {
        return redis.del(lockKey(lease.resource())) == 1;      // TODO lesson 8: this deletes anyone's lock
    }

    /**
     * Pushes the lease's deadline out to {@code lease} from now, but only if the key still holds this lease's token.
     * Returns true if it did. One command on Redis 8.4+: {@code SET key token IFEQ token PX ms}, which is
     * {@code redis.set(k, token, SetParams.setParams().condition(CompareCondition.valueEq(token)).px(ms))} in Jedis
     * and returns "OK" or null.
     */
    public boolean extend(Lease lease, Duration newLease) {
        throw new UnsupportedOperationException("TODO: SET ... IFEQ token PX");
    }
}
