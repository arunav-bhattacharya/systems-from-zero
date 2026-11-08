package sfz.txn.l06.demo;

import io.lettuce.core.RedisFuture;
import io.lettuce.core.api.StatefulRedisConnection;
import io.lettuce.core.api.async.RedisAsyncCommands;
import redis.clients.jedis.AbstractPipeline;
import redis.clients.jedis.RedisClient;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

/** 5,000 SETs three ways: one round trip each, one Jedis pipeline, and Lettuce futures on one connection. */
public class PipelineDemo {
    static final int N = 5_000;

    public static void main(String[] args) throws Exception {
        try (RedisClient jedis = RedisClient.builder().hostAndPort("localhost", 6379).build()) {
            for (int i = 0; i < 2_000; i++) jedis.set("warm:" + i, "1");      // warm up the JIT and the pool

            long t0 = System.nanoTime();
            for (int i = 0; i < N; i++) jedis.set("acct:" + i, "100");         // send, wait, send, wait...
            report("one by one", t0);

            t0 = System.nanoTime();
            try (AbstractPipeline pipe = jedis.pipelined()) {
                for (int i = 0; i < N; i++) pipe.set("acct:" + i, "100");       // buffered, nothing waits
                pipe.sync();                                                    // flush, then read all replies
            }
            report("one Jedis pipeline", t0);
        }

        io.lettuce.core.RedisClient lettuce = io.lettuce.core.RedisClient.create("redis://localhost:6379");
        try (StatefulRedisConnection<String, String> conn = lettuce.connect()) {
            RedisAsyncCommands<String, String> redis = conn.async();
            redis.set("warm", "1").get(1, TimeUnit.SECONDS);
            long t0 = System.nanoTime();
            List<RedisFuture<String>> replies = new ArrayList<>(N);
            for (int i = 0; i < N; i++) replies.add(redis.set("acct:" + i, "100"));   // each call returns at once
            for (RedisFuture<String> r : replies) r.get(5, TimeUnit.SECONDS);
            report("Lettuce async, one connection", t0);
        } finally {
            lettuce.shutdown();
        }
    }

    static void report(String label, long t0) {
        double ms = (System.nanoTime() - t0) / 1e6;
        System.out.printf("%-30s %8.1f ms  %,10.0f SETs/s%n", label, ms, N / (ms / 1000));
    }
}
