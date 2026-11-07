package sfz.redis.l08;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.params.SetParams;
import redis.clients.jedis.util.CompareCondition;

import java.time.Duration;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public final class RedisLock {

    public record Lease(String resource, String token, long fence) {}

    // acquire and number the holder in one command: a fence is handed out only with the lock
    public static final String ACQUIRE = """
            if redis.call('SET', KEYS[1], ARGV[1], 'NX', 'PX', ARGV[2]) then
                return redis.call('INCR', KEYS[2])
            end
            return 0
            """;

    // compare-and-delete: the GET and the DEL can't be split by another client's SET
    public static final String RELEASE = """
            if redis.call('GET', KEYS[1]) == ARGV[1] then
                return redis.call('DEL', KEYS[1])
            end
            return 0
            """;

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

    public Optional<Lease> tryAcquire(String resource, Duration lease) {
        String token = UUID.randomUUID().toString();          // 122 random bits: no other client will ever hold the same
        Object fence = redis.eval(ACQUIRE, List.of(lockKey(resource), fenceKey(resource)),
                List.of(token, String.valueOf(lease.toMillis())));
        long f = (Long) fence;
        return f == 0 ? Optional.empty() : Optional.of(new Lease(resource, token, f));
    }

    public boolean release(Lease lease) {
        Object deleted = redis.eval(RELEASE, List.of(lockKey(lease.resource())), List.of(lease.token()));
        return Long.valueOf(1).equals(deleted);
        // Redis 8.4+: return redis.delex(lockKey(lease.resource()), CompareCondition.valueEq(lease.token())) == 1;
    }

    public boolean extend(Lease lease, Duration newLease) {
        // Redis 8.4+: rewrite the same token with a new deadline, only if the token is still ours
        String reply = redis.set(lockKey(lease.resource()), lease.token(),
                SetParams.setParams().condition(CompareCondition.valueEq(lease.token())).px(newLease.toMillis()));
        return reply != null;
    }
}
