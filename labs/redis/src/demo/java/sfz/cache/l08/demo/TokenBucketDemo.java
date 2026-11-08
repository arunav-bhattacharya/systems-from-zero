package sfz.cache.l08.demo;

import redis.clients.jedis.RedisClient;

import java.util.List;

/** A token bucket and GCRA in Lua: a burst of 10, then one request every 500 ms. The same traffic for both. */
public class TokenBucketDemo {
    // KEYS[1] the bucket (a hash with tokens and ts). ARGV[1] capacity, ARGV[2] ms per new token, ARGV[3] now in ms.
    static final String TOKEN_BUCKET = """
            local capacity = tonumber(ARGV[1])
            local interval = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local b = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
            local tokens, ts = tonumber(b[1]), tonumber(b[2])
            if tokens == nil then                                -- a bucket nobody used yet starts full
                tokens, ts = capacity, now
            end
            local earned = math.floor((now - ts) / interval)     -- whole tokens since ts
            if earned > 0 then
                tokens = math.min(capacity, tokens + earned)
                ts = ts + earned * interval                      -- keep the part of a token not earned yet
            end
            local allowed = 0
            if tokens > 0 then
                tokens = tokens - 1
                allowed = 1
            end
            redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', ts)
            redis.call('PEXPIRE', KEYS[1], capacity * interval)  -- idle that long, it is full again: forget it
            return allowed
            """;

    // KEYS[1] the theoretical arrival time (TAT) in ms. ARGV[1] burst, ARGV[2] ms per request, ARGV[3] now in ms.
    static final String GCRA = """
            local burst = tonumber(ARGV[1])
            local interval = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local tat = tonumber(redis.call('GET', KEYS[1])) or now
            if tat < now then tat = now end                      -- a quiet client: its schedule restarts now
            local next = tat + interval                          -- where this request would push the schedule
            if next - now > burst * interval then return 0 end   -- too far ahead of the allowed rate
            redis.call('SET', KEYS[1], next, 'PX', next - now)   -- once the clock catches up, forget it
            return 1
            """;

    static final String BUCKET_KEY = "demo:l08:bucket:merchant:m-17";
    static final String GCRA_KEY = "demo:l08:gcra:merchant:m-17";

    interface Limiter { boolean take(long now); }

    static void run(String label, Limiter limiter) {
        long t0 = 1_762_500_000_000L;                         // a pretend clock, passed in, so every run is the same
        int burst = 0;
        for (int i = 0; i < 15; i++) if (limiter.take(t0)) burst++;
        StringBuilder line = new StringBuilder();
        int steady = 0;
        for (int i = 1; i <= 20; i++) {
            boolean ok = limiter.take(t0 + i * 250L);
            if (ok) steady++;
            line.append(ok ? '+' : '.');
        }
        int afterRest = 0;
        for (int i = 0; i < 15; i++) if (limiter.take(t0 + 10_000)) afterRest++;
        System.out.printf("%-13s burst of 15 at t = 0: %2d   every 250 ms for 5 s: %2d of 20 %s   burst after 5 quiet s: %2d%n",
                label, burst, steady, line, afterRest);
    }

    public static void main(String[] args) {
        try (RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6379).build()) {
            redis.del(BUCKET_KEY, GCRA_KEY);
            run("token bucket", now -> Long.valueOf(1).equals(
                    redis.eval(TOKEN_BUCKET, List.of(BUCKET_KEY), List.of("10", "500", String.valueOf(now)))));
            run("GCRA", now -> Long.valueOf(1).equals(
                    redis.eval(GCRA, List.of(GCRA_KEY), List.of("10", "500", String.valueOf(now)))));
            System.out.println("token bucket state: " + redis.hgetAll(BUCKET_KEY) + ", PTTL " + redis.pttl(BUCKET_KEY) + " ms");
            System.out.println("GCRA state:         " + redis.get(GCRA_KEY) + ", PTTL " + redis.pttl(GCRA_KEY) + " ms");
        }
    }
}
