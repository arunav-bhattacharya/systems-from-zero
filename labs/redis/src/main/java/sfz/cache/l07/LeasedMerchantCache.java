package sfz.cache.l07;

import redis.clients.jedis.RedisClient;

import java.time.Duration;

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

    /**
     * The fill, run with EVAL. KEYS[1] is the value key, KEYS[2] the lease key. ARGV[1] is the caller's
     * token, ARGV[2] the merchant's name, ARGV[3] the TTL in seconds.
     *
     * <p>If the lease key still holds ARGV[1]: SET the value with EX ARGV[3], DEL the lease, return 1.
     * Otherwise change nothing and return 0. Lua compares strings with {@code ==} and {@code ~=}, and
     * {@code redis.call('GET', ...)} returns {@code false} for a missing key.
     */
    private static final String FILL = "return redis.error_reply('TODO: write the fill script')";

    private final RedisClient redis;
    private final MerchantTable table;
    private final String prefix;
    private final Duration lease;
    private final Duration patience;
    private final Runnable beforeFill;

    /**
     * @param prefix     put in front of every key, so tests don't collide
     * @param lease      how long a lease lives if its holder never fills, for example 10 seconds
     * @param patience   how long a reader that can't get the lease waits for the value, for example 1 second
     * @param beforeFill runs after the table read and before the fill; real code passes {@code () -> {}}
     */
    public LeasedMerchantCache(RedisClient redis, MerchantTable table, String prefix,
                               Duration lease, Duration patience, Runnable beforeFill) {
        this.redis = redis;
        this.table = table;
        this.prefix = prefix;
        this.lease = lease;
        this.patience = patience;
        this.beforeFill = beforeFill;
    }

    /** {@code <prefix>merchant:{<id>}}. Done for you. */
    public String valueKey(String id) {
        return prefix + "merchant:{" + id + "}";
    }

    /** {@code <prefix>lease:{<id>}}: the same hash tag, so on a cluster both keys share a slot (lesson 10). Done for you. */
    public String leaseKey(String id) {
        return prefix + "lease:{" + id + "}";
    }

    /**
     * The merchant's name, or null if the table has no row.
     *
     * <ol>
     *   <li>GET the value. A hit returns it.</li>
     *   <li>On a miss, try to take the lease: {@code SET <leaseKey> <random token> NX PX <lease>}.
     *     <ul>
     *       <li>You got it: read the table. No row: release your lease (only if it is still yours:
     *           {@code redis.delex(key, CompareCondition.valueEq(token))}) and return null. Otherwise run
     *           {@code beforeFill}, EVAL {@link #FILL} with your token, and return the row's name whether
     *           or not the fill was accepted: your read was correct when you made it.</li>
     *       <li>Someone else holds it: sleep 10 ms and start again from step 1, until {@code patience}
     *           has passed.</li>
     *     </ul>
     *   </li>
     *   <li>Out of patience: return the name from the table without filling. Never fill without a lease.</li>
     * </ol>
     */
    @Override
    public String get(String id) {
        throw new UnsupportedOperationException("TODO: GET; on a miss take the lease with SET NX PX, read, fill with the script");
    }

    /** After a write commits: DEL the value and the lease in one command, so no fill that began before the write can land. */
    @Override
    public void afterWrite(String id) {
        throw new UnsupportedOperationException("TODO: DEL the value key and the lease key together");
    }
}
