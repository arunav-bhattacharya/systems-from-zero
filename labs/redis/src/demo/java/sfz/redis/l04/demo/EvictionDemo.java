package sfz.redis.l04.demo;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.exceptions.JedisDataException;

import java.util.ArrayList;
import java.util.List;

/**
 * Fills the tiny lab server (port 6380, maxmemory 4mb) under one eviction policy and reports what survived.
 * 200 hot keys are read before every batch; four batches of 800 cold keys are written once and never read.
 * It empties that server first, so never point it at a Redis you care about.
 */
public class EvictionDemo {
    public static void main(String[] args) throws InterruptedException {
        String policy = args.length > 0 ? args[0] : "allkeys-lru";
        String value = "x".repeat(1_000);
        try (RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6380).build()) {
            redis.flushAll();
            redis.configSet("maxmemory-policy", policy);
            long evictedBefore = stat(redis, "stats", "evicted_keys");
            System.out.println("policy " + policy + ", maxmemory " + stat(redis, "memory", "maxmemory") + " bytes");

            List<String> hot = new ArrayList<>();
            for (int i = 0; i < 200; i++) {
                hot.add("hot:" + i);
                redis.set("hot:" + i, value);
            }
            for (int round = 0; round < 4; round++) {
                Thread.sleep(1_100);                               // let the once-a-second LRU clock move
                for (String k : hot) redis.get(k);                 // read the hot keys: they are young again
                int written = 0;
                String error = null;
                for (int i = 0; i < 800; i++) {
                    try {
                        redis.set("cold:" + round + ":" + i, value);
                        written++;
                    } catch (JedisDataException e) {
                        error = e.getMessage();
                        break;
                    }
                }
                System.out.printf("batch %d: wrote %d cold keys%s%n", round + 1, written, error == null ? "" : ", then: " + error);
                if (error != null) break;
            }

            long hotLeft = hot.stream().filter(redis::exists).count();
            StringBuilder cold = new StringBuilder();
            for (int round = 0; round < 4; round++) {
                int left = 0;
                for (int i = 0; i < 800; i++) if (redis.exists("cold:" + round + ":" + i)) left++;
                cold.append(round == 0 ? "" : ", ").append(left);
            }
            System.out.println("hot keys left: " + hotLeft + " of 200");
            System.out.println("cold keys left per batch: " + cold);
            System.out.println("evicted_keys: " + (stat(redis, "stats", "evicted_keys") - evictedBefore)
                    + ", used_memory: " + stat(redis, "memory", "used_memory"));
        }
    }

    static long stat(RedisClient redis, String section, String field) {
        for (String line : redis.info(section).split("\r\n")) {
            if (line.startsWith(field + ":")) return Long.parseLong(line.substring(field.length() + 1).trim());
        }
        throw new IllegalArgumentException(field);
    }
}
