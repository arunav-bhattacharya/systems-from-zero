package sfz.cache.l06;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.params.SetParams;

import java.util.Random;

public final class MerchantCache {
    public static final String MISSING = "<missing>";

    private final RedisClient redis;
    private final String prefix;
    private final MerchantRepository repository;
    private final long ttlSeconds;
    private final double jitter;
    private final long missingTtlSeconds;
    private final Random random;
    private final SingleFlight<Merchant> flights = new SingleFlight<>();

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

    public String key(String id) {
        return prefix + "merchant:" + id;
    }

    public Merchant get(String id) {
        String cached = redis.get(key(id));
        if (cached != null) return decode(cached);              // a hit, positive or negative: no database
        // a miss: one loader per merchant in this JVM, however many threads missed together
        return flights.load(id, () -> {
            String again = redis.get(key(id));                  // a flight that just finished may have filled it
            if (again != null) return decode(again);
            Merchant m = repository.find(id);
            if (m == null) {
                // remember "not found" briefly, so a flood of bad ids doesn't reach the database
                redis.set(key(id), MISSING, SetParams.setParams().ex(missingTtlSeconds));
            } else {
                redis.set(key(id), m.encode(), SetParams.setParams().ex(jitteredTtl(ttlSeconds, jitter, random)));
            }
            return m;
        });
    }

    public void invalidate(String id) {
        redis.del(key(id));                                     // delete, don't overwrite: the next read reloads
    }

    public static long jitteredTtl(long baseSeconds, double jitter, Random random) {
        double factor = 1 + (random.nextDouble() * 2 - 1) * jitter;   // uniform in [1 - jitter, 1 + jitter]
        return Math.max(1, Math.round(baseSeconds * factor));
    }

    private static Merchant decode(String cached) {
        return MISSING.equals(cached) ? null : Merchant.decode(cached);
    }
}
