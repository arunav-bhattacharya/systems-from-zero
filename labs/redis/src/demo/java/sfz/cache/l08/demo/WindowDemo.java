package sfz.cache.l08.demo;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.params.IncrexParams;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Limit: 5 requests per card per minute. A fixed window, a sliding window, and a sliding window done without a script. */
public class WindowDemo {
    static final int LIMIT = 5;
    static final long MINUTE = 60_000;
    static final long BASE = 1_762_500_000_000L;                  // a time that starts a new minute (it divides by 60,000)

    static final String SLIDING = """
            local now, window, limit = tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3])
            redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
            if redis.call('ZCARD', KEYS[1]) >= limit then return 0 end
            redis.call('ZADD', KEYS[1], now, ARGV[4])
            redis.call('PEXPIRE', KEYS[1], window)
            return 1
            """;

    static boolean fixed(RedisClient redis, String card, long now) {
        String key = "demo:l08:fixed:" + card + ":" + (now / MINUTE);   // one counter per card per minute
        // Redis 8.8: +1 unless that passes 5, and a 60 s TTL set by the same command (ENX: only when there is none)
        List<Long> reply = redis.increx(key, 1, IncrexParams.increxParams().ubound(LIMIT).ex(60).enx());
        return reply.get(1) == 1;                                        // [new value, applied increment]
    }

    static boolean sliding(RedisClient redis, String card, long now) {
        Object r = redis.eval(SLIDING, List.of("demo:l08:sliding:" + card),
                List.of(String.valueOf(now), String.valueOf(MINUTE), String.valueOf(LIMIT), UUID.randomUUID().toString()));
        return Long.valueOf(1).equals(r);
    }

    static boolean slidingWithoutScript(RedisClient redis, String card, long now) {
        String key = "demo:l08:sliding:" + card;
        redis.zremrangeByScore(key, Double.NEGATIVE_INFINITY, now - MINUTE);
        if (redis.zcard(key) >= LIMIT) return false;                    // another pod can run between this and the ZADD
        redis.zadd(key, now, UUID.randomUUID().toString());
        redis.pexpire(key, MINUTE);
        return true;
    }

    interface Limiter { boolean tryAcquire(RedisClient redis, String card, long now); }

    static int burstAtOneInstant(RedisClient redis, Limiter limiter, String card) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(32);
        CountDownLatch start = new CountDownLatch(1);
        List<CompletableFuture<Boolean>> calls = new ArrayList<>();
        for (int i = 0; i < 32; i++) {
            calls.add(CompletableFuture.supplyAsync(() -> {
                try { start.await(); } catch (InterruptedException e) { throw new RuntimeException(e); }
                return limiter.tryAcquire(redis, card, BASE);
            }, pool));
        }
        start.countDown();
        int admitted = 0;
        for (CompletableFuture<Boolean> c : calls) if (c.get()) admitted++;
        pool.shutdown();
        return admitted;
    }

    public static void main(String[] args) throws Exception {
        try (RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6379).build()) {
            redis.del("demo:l08:fixed:card:7:" + (BASE / MINUTE), "demo:l08:fixed:card:7:" + (BASE / MINUTE + 1),
                    "demo:l08:sliding:card:7", "demo:l08:sliding:card:8", "demo:l08:sliding:card:9");   // start clean

            // five requests at 0:59.0 to 0:59.4, then five at 1:00.0 to 1:00.4
            long[] times = new long[10];
            for (int i = 0; i < 5; i++) {
                times[i] = BASE + 59_000 + i * 100;
                times[i + 5] = BASE + MINUTE + i * 100;
            }
            int f = 0, s = 0;
            for (long t : times) {
                if (fixed(redis, "card:7", t)) f++;
                if (sliding(redis, "card:7", t)) s++;
            }
            System.out.println("Limit: 5 per card per minute. Ten requests within 1.4 s, across a minute boundary:");
            System.out.printf("  fixed window, INCREX per minute    admitted %2d of 10%n", f);
            System.out.printf("  sliding window, one Lua script     admitted %2d of 10%n", s);

            System.out.println("32 requests for card:8 at the same instant, from 32 threads:");
            System.out.printf("  sliding window, ZCARD then ZADD    admitted %2d of 32%n",
                    burstAtOneInstant(redis, WindowDemo::slidingWithoutScript, "card:8"));
            System.out.printf("  sliding window, one Lua script     admitted %2d of 32%n",
                    burstAtOneInstant(redis, WindowDemo::sliding, "card:9"));
        }
    }
}
