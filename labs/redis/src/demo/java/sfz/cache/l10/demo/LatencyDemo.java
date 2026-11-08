package sfz.cache.l10.demo;

import redis.clients.jedis.CommandArguments;
import redis.clients.jedis.DefaultJedisClientConfig;
import redis.clients.jedis.Protocol;
import redis.clients.jedis.RedisClient;
import redis.clients.jedis.params.ScanParams;
import redis.clients.jedis.resps.ScanResult;
import redis.clients.jedis.resps.Slowlog;

import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Loads 1,000,000 payments, then looks for refund keys twice while a second client sends GETs back to back:
 * once with KEYS (one command walks the whole keyspace) and once with SCAN (a thousand small steps).
 * Prints the slowest GET during each, the slow log's top entry, then deletes its keys.
 */
public class LatencyDemo {
    static final String PREFIX = "demo:l10:payment:";
    static final String FILL = """
            for i = tonumber(ARGV[1]), tonumber(ARGV[2]) do redis.call('SET', KEYS[1] .. i, 'settled') end
            return 1
            """;
    static final String CLEAN = """
            for i = tonumber(ARGV[1]), tonumber(ARGV[2]) do redis.call('UNLINK', KEYS[1] .. i) end
            return 1
            """;
    static final int N = 1_000_000;

    public static void main(String[] args) throws Exception {
        // a busy server can take more than the default 2 s to answer: wait up to 30 s
        try (RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6379)
                .clientConfig(DefaultJedisClientConfig.builder().socketTimeoutMillis(30_000).build()).build()) {
            for (int from = 1; from <= N; from += 100_000) {
                redis.eval(FILL, 1, PREFIX, String.valueOf(from), String.valueOf(from + 99_999));
            }
            redis.slowlogReset();
            System.out.printf("loaded %,d payments; %,d keys in the database%n", N, redis.dbSize());

            long[] keys = whileReading(redis, () -> redis.keys("demo:l10:refund:*"));
            System.out.printf("KEYS: 1 command, %,5d ms in all; the slowest GET meanwhile waited %,4d ms%n", keys[0], keys[1]);

            AtomicLong calls = new AtomicLong();
            long[] scan = whileReading(redis, () -> {
                ScanParams match = new ScanParams().match("demo:l10:refund:*").count(1_000);
                String cursor = ScanParams.SCAN_POINTER_START;
                do {
                    ScanResult<String> page = redis.scan(cursor, match);
                    calls.incrementAndGet();
                    cursor = page.getCursor();
                } while (!cursor.equals(ScanParams.SCAN_POINTER_START));
            });
            System.out.printf("SCAN: %,d commands, %,5d ms in all; the slowest GET meanwhile waited %,4d ms%n", calls.get(), scan[0], scan[1]);

            @SuppressWarnings("unchecked")
            List<Slowlog> log = Slowlog.from((List<Object>) redis.executeCommand(new CommandArguments(Protocol.Command.SLOWLOG).add("GET").add(128)));
            Slowlog top = log.stream().max((a, b) -> Long.compare(a.getExecutionTime(), b.getExecutionTime())).orElseThrow();
            System.out.printf("entries in the slow log: %d; the slowest: %s, %,d microseconds%n", log.size(), top.getArgs(), top.getExecutionTime());

            for (int from = 1; from <= N; from += 100_000) {
                redis.eval(CLEAN, 1, PREFIX, String.valueOf(from), String.valueOf(from + 99_999));
            }
        }
    }

    /** Runs {@code task} while a second thread sends GETs back to back; returns {task ms, slowest GET in ms}. */
    static long[] whileReading(RedisClient redis, Runnable task) throws InterruptedException {
        AtomicBoolean running = new AtomicBoolean(true);
        AtomicLong slowestNanos = new AtomicLong();
        Thread reader = new Thread(() -> {
            while (running.get()) {
                long t0 = System.nanoTime();
                redis.get(PREFIX + 42);
                slowestNanos.accumulateAndGet(System.nanoTime() - t0, Math::max);
            }
        });
        reader.start();
        Thread.sleep(200);
        slowestNanos.set(0);                                         // only count what happens during the task
        long t0 = System.nanoTime();
        task.run();
        long ms = (System.nanoTime() - t0) / 1_000_000;
        running.set(false);
        reader.join();
        return new long[] {ms, slowestNanos.get() / 1_000_000};
    }
}
