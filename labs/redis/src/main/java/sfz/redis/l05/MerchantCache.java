package sfz.redis.l05;

import redis.clients.jedis.RedisClient;

import java.util.Random;

/**
 * A cache-aside cache of merchant profiles in Redis, in front of a slow {@link MerchantRepository}.
 *
 * <p>Each merchant lives under {@link #key(String)} as {@link Merchant#encode()}, with a TTL of about
 * {@code ttlSeconds}, spread by {@code jitter} so that keys loaded together don't expire together.
 * A merchant that doesn't exist is cached too, as the string {@link #MISSING}, for the shorter
 * {@code missingTtlSeconds}. Concurrent misses for one merchant go through {@link SingleFlight}, so
 * the repository sees one load, not one per thread.
 */
public final class MerchantCache {
    /** What the cache stores for a merchant the repository doesn't have (a negative entry). */
    public static final String MISSING = "<missing>";

    private final RedisClient redis;
    private final String prefix;
    private final MerchantRepository repository;
    private final long ttlSeconds;
    private final double jitter;
    private final long missingTtlSeconds;
    private final Random random;
    private final SingleFlight<Merchant> flights = new SingleFlight<>();

    /**
     * @param prefix            put in front of every key, so tests don't collide
     * @param ttlSeconds        the base TTL for a merchant, for example 3,600
     * @param jitter            the spread, for example 0.1 for plus or minus 10%
     * @param missingTtlSeconds the TTL for a negative entry, for example 60
     * @param seed              seeds {@code random}, so runs are repeatable
     */
    public MerchantCache(RedisClient redis, String prefix, MerchantRepository repository,
                         long ttlSeconds, double jitter, long missingTtlSeconds, long seed) {
        this.redis = redis;
        this.prefix = prefix;
        this.repository = repository;
        this.ttlSeconds = ttlSeconds;
        this.jitter = jitter;
        this.missingTtlSeconds = missingTtlSeconds;
        this.random = new Random(seed);
    }

    /** The Redis key for a merchant: {@code <prefix>merchant:<id>}. Done for you. */
    public String key(String id) {
        return prefix + "merchant:" + id;
    }

    /**
     * The merchant with this id, or null if the repository has none.
     *
     * <ol>
     *   <li>GET the key. A hit returns at once: {@link #MISSING} means null, anything else is
     *       {@link Merchant#decode(String)}.</li>
     *   <li>A miss goes through {@code flights.load(id, () -> ...)}. Inside the loader, GET the key once more
     *       (a flight that just finished may have filled it), then call the repository.</li>
     *   <li>Store what you found with {@code SetParams.setParams().ex(...)}: the encoded merchant with
     *       {@link #jitteredTtl}, or {@link #MISSING} with {@code missingTtlSeconds}.</li>
     * </ol>
     */
    public Merchant get(String id) {
        throw new UnsupportedOperationException("TODO: GET, and on a miss load once through flights, then SET with EX");
    }

    /** Call this after the merchant changes in the database: DEL the key, so the next read loads the new row. */
    public void invalidate(String id) {
        throw new UnsupportedOperationException("TODO: DEL the key");
    }

    /**
     * {@code baseSeconds} times a random factor between {@code 1 - jitter} and {@code 1 + jitter}, rounded,
     * and never below 1. With 3,600 and 0.1 the result is uniform between 3,240 and 3,960.
     * {@code random.nextDouble()} is uniform in [0, 1).
     */
    public static long jitteredTtl(long baseSeconds, double jitter, Random random) {
        throw new UnsupportedOperationException("TODO: base * (1 + u * jitter) with u uniform in [-1, 1]");
    }
}
