package sfz.cache.l06.demo;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.params.SetParams;

/** Cache-aside in front of a "database" that takes 120 ms: one miss, then hits. */
public class CacheAsideDemo {
    static int dbCalls = 0;

    // the system of record: in production an Oracle query behind a connection pool
    static String loadFromDatabase(String id) throws InterruptedException {
        dbCalls++;
        Thread.sleep(120);
        return id + "|Fietsen Utrecht|NL|5940";
    }

    static String getMerchant(RedisClient redis, String id) throws InterruptedException {
        String key = "merchant:" + id;
        String cached = redis.get(key);                                  // 1. ask Redis first
        if (cached != null) return cached;
        String row = loadFromDatabase(id);                               // 2. a miss: go to the database
        redis.set(key, row, SetParams.setParams().ex(3_600));            // 3. keep it for an hour
        return row;
    }

    public static void main(String[] args) throws InterruptedException {
        try (RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6379).build()) {
            redis.del("merchant:m-17");
            redis.get("warm-up");                                        // open a pooled connection first
            for (int i = 1; i <= 4; i++) {
                long t0 = System.nanoTime();
                String row = getMerchant(redis, "m-17");
                System.out.printf("read %d: %-30s %7.2f ms  (database calls so far: %d)%n",
                        i, row, (System.nanoTime() - t0) / 1e6, dbCalls);
            }
            System.out.println("TTL merchant:m-17 = " + redis.ttl("merchant:m-17") + " s");
        }
    }
}
