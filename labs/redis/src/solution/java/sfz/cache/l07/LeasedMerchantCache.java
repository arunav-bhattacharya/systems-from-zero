package sfz.cache.l07;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.params.SetParams;
import redis.clients.jedis.util.CompareCondition;

import java.time.Duration;
import java.util.List;
import java.util.UUID;

/**
 * Cache-aside with memcache-style leases (Nishtala et al., "Scaling Memcache at Facebook", NSDI 2013),
 * built from {@code SET NX PX} and one Lua script.
 *
 * <p>A reader that misses may fill the value only while it holds the key's lease: a random token kept in
 * its own key, {@link #leaseKey(String)}, with a short TTL. A write deletes the value and the lease in one
 * command, so a reader that read the table before the write finds its lease gone, and its fill is refused.
 * A reader that misses while someone else holds the lease waits a little for the value instead of querying
 * the table too.
 */
public final class LeasedMerchantCache implements MerchantCache {
    /** How long a filled value lives: the backstop, not the fix. */
    public static final long TTL_SECONDS = 3_600;

    // one command on Redis's single thread: nothing can run between the lease check and the SET
    private static final String FILL = """
            if redis.call('GET', KEYS[2]) ~= ARGV[1] then return 0 end   -- revoked by a write, or someone else's
            redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
            redis.call('DEL', KEYS[2])                                    -- done: the next miss may take a new lease
            return 1
            """;

    private final RedisClient redis;
    private final MerchantTable table;
    private final String prefix;
    private final Duration lease;
    private final Duration patience;
    private final Runnable beforeFill;

    public LeasedMerchantCache(RedisClient redis, MerchantTable table, String prefix,
                               Duration lease, Duration patience, Runnable beforeFill) {
        this.redis = redis;
        this.table = table;
        this.prefix = prefix;
        this.lease = lease;
        this.patience = patience;
        this.beforeFill = beforeFill;
    }

    public String valueKey(String id) {
        return prefix + "merchant:{" + id + "}";
    }

    public String leaseKey(String id) {
        return prefix + "lease:{" + id + "}";
    }

    @Override
    public String get(String id) {
        long giveUpAt = System.nanoTime() + patience.toNanos();
        while (true) {
            String cached = redis.get(valueKey(id));
            if (cached != null) return cached;                                // a hit

            String token = UUID.randomUUID().toString();
            String took = redis.set(leaseKey(id), token, SetParams.setParams().nx().px(lease.toMillis()));
            if (took != null) {                                               // the lease is ours: we load
                MerchantTable.Row row = table.read(id);
                if (row == null) {
                    redis.delex(leaseKey(id), CompareCondition.valueEq(token)); // Redis 8.4+: only if still ours
                    return null;
                }
                beforeFill.run();
                redis.eval(FILL, List.of(valueKey(id), leaseKey(id)),
                        List.of(token, row.getName(), String.valueOf(TTL_SECONDS)));  // refused if a write came in between
                return row.getName();
            }

            if (System.nanoTime() >= giveUpAt) break;                         // someone else is loading: wait a bit
            sleep(10);
        }
        MerchantTable.Row row = table.read(id);                               // out of patience: read, but never fill
        return row == null ? null : row.getName();
    }

    @Override
    public void afterWrite(String id) {
        redis.del(valueKey(id), leaseKey(id));                                // one command: both go together
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted while waiting for the lease holder", e);
        }
    }
}
