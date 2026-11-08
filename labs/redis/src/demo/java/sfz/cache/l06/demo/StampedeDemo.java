package sfz.cache.l06.demo;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.params.SetParams;
import redis.clients.jedis.util.CompareCondition;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

/** 100 requests miss the same cold key at once. How many reach the 200 ms database? */
public class StampedeDemo {
    static final String KEY = "merchant:m-17";
    static final AtomicInteger dbCalls = new AtomicInteger();

    static String loadFromDatabase() {
        dbCalls.incrementAndGet();
        sleep(200);
        return "m-17|Fietsen Utrecht|NL|5940";
    }

    /** One service instance: its own Redis client and its own in-process single-flight map. */
    static final class Pod {
        final RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6379).build();
        final ConcurrentHashMap<String, CompletableFuture<String>> flights = new ConcurrentHashMap<>();

        String plain() {                                       // cache-aside, no protection
            String v = redis.get(KEY);
            if (v != null) return v;
            v = loadFromDatabase();
            redis.set(KEY, v, SetParams.setParams().ex(3_600));
            return v;
        }

        String singleFlight() {                                // one load per key per pod
            String v = redis.get(KEY);
            if (v != null) return v;
            CompletableFuture<String> mine = new CompletableFuture<>();
            CompletableFuture<String> running = flights.putIfAbsent(KEY, mine);
            if (running != null) return running.join();        // a follower waits for the leader
            try {
                String row = redis.get(KEY);                   // filled while we became leader?
                if (row == null) {
                    row = loadFromDatabase();
                    redis.set(KEY, row, SetParams.setParams().ex(3_600));
                }
                mine.complete(row);
                return row;
            } finally {
                flights.remove(KEY, mine);
            }
        }

        String redisLock() {                                   // one load per key across all pods
            String v = redis.get(KEY);
            if (v != null) return v;
            String token = UUID.randomUUID().toString();
            if (redis.set("lock:" + KEY, token, SetParams.setParams().nx().px(2_000)) != null) {
                try {
                    v = loadFromDatabase();
                    redis.set(KEY, v, SetParams.setParams().ex(3_600));
                    return v;
                } finally {
                    // Redis 8.4+: delete the lock only if it is still ours (it may have expired and gone to another pod)
                    redis.delex("lock:" + KEY, CompareCondition.valueEq(token));
                }
            }
            for (int i = 0; i < 100; i++) {                    // someone else is loading: wait for the cache
                sleep(10);
                v = redis.get(KEY);
                if (v != null) return v;
            }
            return loadFromDatabase();                         // waited a second: load it ourselves
        }
    }

    interface Strategy { String get(Pod pod); }

    static void run(String label, int pods, Strategy strategy) throws Exception {
        List<Pod> fleet = new ArrayList<>();
        for (int i = 0; i < pods; i++) fleet.add(new Pod());
        fleet.get(0).redis.del(KEY, "lock:" + KEY);
        dbCalls.set(0);
        ExecutorService threads = Executors.newFixedThreadPool(100);
        CountDownLatch start = new CountDownLatch(1);
        List<CompletableFuture<String>> requests = new ArrayList<>();
        for (int i = 0; i < 100; i++) {
            Pod pod = fleet.get(i % pods);
            requests.add(CompletableFuture.supplyAsync(() -> { await(start); return strategy.get(pod); }, threads));
        }
        long t0 = System.nanoTime();
        start.countDown();
        requests.forEach(CompletableFuture::join);
        System.out.printf("%-40s database calls: %3d   %4d ms%n", label, dbCalls.get(), (System.nanoTime() - t0) / 1_000_000);
        threads.shutdown();
        fleet.forEach(p -> p.redis.close());
    }

    public static void main(String[] args) throws Exception {
        run("no protection, 1 pod", 1, Pod::plain);
        run("single-flight, 1 pod", 1, Pod::singleFlight);
        run("single-flight, 4 pods", 4, Pod::singleFlight);
        run("Redis lock (SET NX PX), 4 pods", 4, Pod::redisLock);
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { throw new RuntimeException(e); }
    }

    static void await(CountDownLatch latch) {
        try { latch.await(); } catch (InterruptedException e) { throw new RuntimeException(e); }
    }
}
