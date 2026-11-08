package sfz.cache.l07.demo;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.params.SetParams;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** The stale-set race four times, always in the same order: reader A misses, the writer commits, A fills, B reads. */
public class StaleSetDemo {
    record Row(String name, long version) {}

    static final Map<String, Row> table = new ConcurrentHashMap<>();             // the "database"
    static final RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6379).build();
    static final String KEY = "demo:l07:merchant:{m-17}";
    static final String LEASE = "demo:l07:lease:{m-17}";

    /** What a pod does on a read, and what the writer does after its commit. */
    interface Cache {
        String get(String who, Runnable beforeFill);
        void afterWrite(long newVersion);
    }

    static void say(String who, String what) {
        System.out.printf("  %s  %s%n", who, what);
    }

    // 1. lesson 6's cache-aside: GET, on a miss SELECT and SET; after a write, DEL
    static final Cache NAIVE = new Cache() {
        public String get(String who, Runnable beforeFill) {
            String hit = redis.get(KEY);
            if (hit != null) return hit;
            Row row = table.get("m-17");
            say(who, "GET: miss. SELECT: " + row.name() + " (v" + row.version() + ")");
            beforeFill.run();
            redis.set(KEY, row.name(), SetParams.setParams().ex(3_600));
            say(who, "SET " + row.name() + " EX 3600: OK");
            return row.name();
        }
        public void afterWrite(long v) {
            say("W", "DEL: " + redis.del(KEY) + " keys deleted");
        }
    };

    // 2. a lease: only the reader whose token is still in the lease key may fill
    static final String FILL_WITH_LEASE = """
            if redis.call('GET', KEYS[2]) ~= ARGV[1] then return 0 end
            redis.call('SET', KEYS[1], ARGV[2], 'EX', 3600)
            redis.call('DEL', KEYS[2])
            return 1
            """;

    static final Cache LEASED = new Cache() {
        public String get(String who, Runnable beforeFill) {
            String hit = redis.get(KEY);
            if (hit != null) return hit;
            String token = "t-" + who;                                       // readable; real code uses a UUID
            String took = redis.set(LEASE, token, SetParams.setParams().nx().px(10_000));
            Row row = table.get("m-17");
            say(who, "GET: miss. SET lease " + token + " NX PX 10000: " + took + ". SELECT: " + row.name() + " (v" + row.version() + ")");
            beforeFill.run();
            Object ok = redis.eval(FILL_WITH_LEASE, List.of(KEY, LEASE), List.of(token, row.name()));
            say(who, "fill with lease " + token + ": " + (Long.valueOf(1).equals(ok) ? "stored" : "refused, the lease is gone"));
            return row.name();
        }
        public void afterWrite(long v) {
            say("W", "DEL value and lease: " + redis.del(KEY, LEASE) + " keys deleted");
        }
    };

    // 3 and 4. a version check: the entry is a hash {ver, name}; a fill older than what the cache has seen is refused
    static final String FILL_IF_NEWER = """
            local seen = tonumber(redis.call('HGET', KEYS[1], 'ver'))
            if seen and seen > tonumber(ARGV[1]) then return 0 end
            redis.call('HSET', KEYS[1], 'ver', ARGV[1], 'name', ARGV[2])
            redis.call('EXPIRE', KEYS[1], 3600)
            return 1
            """;
    static final String TOMBSTONE = """
            local seen = tonumber(redis.call('HGET', KEYS[1], 'ver'))
            if seen and seen > tonumber(ARGV[1]) then return 0 end
            redis.call('DEL', KEYS[1])
            redis.call('HSET', KEYS[1], 'ver', ARGV[1])
            redis.call('PEXPIRE', KEYS[1], ARGV[2])
            return 1
            """;

    static Cache versioned(boolean tombstone) {
        return new Cache() {
            public String get(String who, Runnable beforeFill) {
                String hit = redis.hget(KEY, "name");                        // a tombstone has no name: a miss
                if (hit != null) return hit;
                Row row = table.get("m-17");
                say(who, "HGET: miss. SELECT: " + row.name() + " (v" + row.version() + ")");
                beforeFill.run();
                Object ok = redis.eval(FILL_IF_NEWER, List.of(KEY), List.of(String.valueOf(row.version()), row.name()));
                say(who, "fill v" + row.version() + " if newer: " + (Long.valueOf(1).equals(ok)
                        ? "stored" : "refused, the cache has seen v" + redis.hget(KEY, "ver")));
                return row.name();
            }
            public void afterWrite(long v) {
                if (tombstone) {
                    redis.eval(TOMBSTONE, List.of(KEY), List.of(String.valueOf(v), "10000"));
                    say("W", "tombstone: ver " + v + ", no name, for 10 s");
                } else {
                    say("W", "DEL: " + redis.del(KEY) + " keys deleted");
                }
            }
        };
    }

    static void race(String title, Cache cache) throws Exception {
        redis.del(KEY, LEASE);
        table.put("m-17", new Row("Fietsen Utrecht", 1));
        System.out.println(title);
        CountDownLatch atFill = new CountDownLatch(1);
        CountDownLatch writerDone = new CountDownLatch(1);

        // reader A misses, reads v1, and stops just before its fill until the writer is done
        CompletableFuture<String> readerA = CompletableFuture.supplyAsync(() -> cache.get("A", () -> {
            atFill.countDown();
            await(writerDone);
        }));
        await(atFill);
        table.put("m-17", new Row("Velo Utrecht", 2));
        say("W", "UPDATE: Velo Utrecht (v2). COMMIT");
        cache.afterWrite(2);
        writerDone.countDown();
        readerA.get(5, TimeUnit.SECONDS);

        String b = cache.get("B", () -> {});
        String db = table.get("m-17").name();
        System.out.println("  B  reads: " + b + (b.equals(db) ? "  (fresh)"
                : "  (STALE: the database says " + db + ", and the entry lives " + redis.ttl(KEY) + " s more)"));
        System.out.println();
    }

    static void await(CountDownLatch latch) {
        try {
            if (!latch.await(5, TimeUnit.SECONDS)) throw new IllegalStateException("timed out");
        } catch (InterruptedException e) {
            throw new IllegalStateException(e);
        }
    }

    public static void main(String[] args) throws Exception {
        race("1. cache-aside, DEL after the commit", NAIVE);
        race("2. a lease that the DEL revokes", LEASED);
        race("3. a version check, DEL after the commit", versioned(false));
        race("4. a version check, a tombstone after the commit", versioned(true));
        System.out.println("cleaning up: " + redis.del(KEY, LEASE) + " keys deleted");
        redis.close();
    }
}
