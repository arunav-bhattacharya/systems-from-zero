package sfz.redis.l10.demo;

import redis.clients.jedis.CommandArguments;
import redis.clients.jedis.DefaultJedisClientConfig;
import redis.clients.jedis.Protocol;
import redis.clients.jedis.RedisClient;

import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Loads 1,000,000 payments, then snapshots them twice while a second client keeps updating payments:
 * once with SAVE (the main thread writes the file itself) and once with BGSAVE (a forked child writes it).
 * Prints how many updates got through and the slowest one, then deletes its keys.
 */
public class SnapshotDemo {
    static final String PREFIX = "demo:l10:payment:";
    static final String FILL = """
            for i = tonumber(ARGV[1]), tonumber(ARGV[2]) do
                redis.call('SET', KEYS[1] .. i, 'settled:EUR:1250:merchant-' .. (i % 500))
            end
            return 1
            """;
    static final String CLEAN = """
            for i = tonumber(ARGV[1]), tonumber(ARGV[2]) do redis.call('UNLINK', KEYS[1] .. i) end
            return 1
            """;
    static final int N = 1_000_000;

    public static void main(String[] args) throws Exception {
        // SAVE holds the server for seconds: wait up to 30 s for a reply instead of the default 2 s
        try (RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6379)
                .clientConfig(DefaultJedisClientConfig.builder().socketTimeoutMillis(30_000).build()).build()) {
            for (int from = 1; from <= N; from += 100_000) {     // in slices of 100,000, so no script runs for long
                redis.eval(FILL, 1, PREFIX, String.valueOf(from), String.valueOf(from + 99_999));
            }
            System.out.printf("loaded %,d payments, used_memory %d MB%n", N, stat(redis, "memory", "used_memory") / 1_000_000);
            if (stat(redis, "persistence", "rdb_bgsave_in_progress") == 1) {
                // a million changes trip the default save point "60 10000": the server started a BGSAVE by itself
                System.out.println("a save point already started a BGSAVE; waiting for it to finish");
                while (stat(redis, "persistence", "rdb_bgsave_in_progress") == 1) pause(50);
            }

            long[] save = whileUpdating(redis, () -> redis.executeCommand(new CommandArguments(Protocol.Command.SAVE)));
            System.out.printf("SAVE:   %,6d ms; updates done meanwhile: %,5d; slowest update: %,5d ms%n", save[0], save[1], save[2]);

            long[] bg = whileUpdating(redis, () -> {
                redis.executeCommand(new CommandArguments(Protocol.Command.BGSAVE));          // forks, then answers at once
                while (stat(redis, "persistence", "rdb_bgsave_in_progress") == 1) pause(5);
            });
            System.out.printf("BGSAVE: %,6d ms; updates done meanwhile: %,5d; slowest update: %,5d ms%n", bg[0], bg[1], bg[2]);
            System.out.printf("        fork took %.1f ms, the child copied %.1f MB of pages the parent changed meanwhile%n",
                    stat(redis, "stats", "latest_fork_usec") / 1000.0, stat(redis, "persistence", "rdb_last_cow_size") / 1e6);

            for (int from = 1; from <= N; from += 100_000) {
                redis.eval(CLEAN, 1, PREFIX, String.valueOf(from), String.valueOf(from + 99_999));
            }
        }
    }

    /** Runs {@code snapshot} while a second thread updates random payments; returns {ms, updates, slowest update in ms}. */
    static long[] whileUpdating(RedisClient redis, Runnable snapshot) throws InterruptedException {
        AtomicBoolean running = new AtomicBoolean(true);
        AtomicLong updates = new AtomicLong();
        AtomicLong slowestNanos = new AtomicLong();
        Thread writer = new Thread(() -> {
            while (running.get()) {
                long t0 = System.nanoTime();
                redis.set(PREFIX + ThreadLocalRandom.current().nextInt(1, N + 1), "refunded");
                slowestNanos.accumulateAndGet(System.nanoTime() - t0, Math::max);
                updates.incrementAndGet();
            }
        });
        writer.start();
        pause(200);                                                  // let the writer get going first
        long before = updates.get();
        long t0 = System.nanoTime();
        snapshot.run();
        long ms = (System.nanoTime() - t0) / 1_000_000;
        long during = updates.get() - before;
        running.set(false);
        writer.join();
        return new long[] {ms, during, slowestNanos.get() / 1_000_000};
    }

    static long stat(RedisClient redis, String section, String field) {
        for (String line : redis.info(section).split("\r\n")) {
            if (line.startsWith(field + ":")) return Long.parseLong(line.substring(field.length() + 1).trim());
        }
        throw new IllegalArgumentException(field);
    }

    static void pause(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            throw new IllegalStateException(e);
        }
    }
}
