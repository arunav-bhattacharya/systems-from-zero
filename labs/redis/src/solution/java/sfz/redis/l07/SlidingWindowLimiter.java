package sfz.redis.l07;

import redis.clients.jedis.RedisClient;

import java.util.List;
import java.util.UUID;

public final class SlidingWindowLimiter {

    // trim, count, decide and record inside one command: no other client can run between ZCARD and ZADD
    public static final String SCRIPT = """
            local now = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local limit = tonumber(ARGV[3])
            redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)    -- drop t <= now - window
            if redis.call('ZCARD', KEYS[1]) >= limit then
                return 0
            end
            redis.call('ZADD', KEYS[1], now, ARGV[4])
            redis.call('PEXPIRE', KEYS[1], window)
            return 1
            """;

    private final RedisClient redis;
    private final String prefix;
    private final int limit;
    private final long windowMillis;

    public SlidingWindowLimiter(RedisClient redis, String prefix, int limit, long windowMillis) {
        this.redis = redis;
        this.prefix = prefix;
        this.limit = limit;
        this.windowMillis = windowMillis;
    }

    public String key(String subject) {
        return prefix + subject;
    }

    public boolean tryAcquire(String subject, long nowMillis) {
        // the member must be unique: two requests in the same millisecond would otherwise collapse into one entry
        String member = UUID.randomUUID().toString();
        Object admitted = redis.eval(SCRIPT, List.of(key(subject)),
                List.of(String.valueOf(nowMillis), String.valueOf(windowMillis), String.valueOf(limit), member));
        return Long.valueOf(1).equals(admitted);
    }
}
