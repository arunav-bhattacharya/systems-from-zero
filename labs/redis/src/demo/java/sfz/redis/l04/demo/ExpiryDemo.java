package sfz.redis.l04.demo;

import redis.clients.jedis.RedisClient;

/**
 * Creates 500,000 idempotency keys that all expire 3 seconds later, then watches how Redis reclaims them:
 * a GET says the key is gone at once, while DBSIZE and used_memory fall only as the active expiry cycle works.
 */
public class ExpiryDemo {
    static final String CREATE = """
            for i = 1, tonumber(ARGV[1]) do
                redis.call('SET', 'idem:' .. i, 'done', 'PX', ARGV[2])
            end
            return redis.call('DBSIZE')
            """;

    public static void main(String[] args) throws InterruptedException {
        try (RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6379).build()) {
            long expiredBefore = stat(redis, "expired_keys");
            long start = System.nanoTime();
            // one script, so every key gets the same deadline: the script's start time plus 3,000 ms
            redis.eval(CREATE, 0, "500000", "3000");
            System.out.printf("created 500,000 keys in %d ms, used_memory %d MB%n",
                    (System.nanoTime() - start) / 1_000_000, stat(redis, "used_memory") / 1_000_000);
            Thread.sleep(2_700 - (System.nanoTime() - start) / 1_000_000);
            for (int i = 0; i < 12; i++) {
                long ms = (System.nanoTime() - start) / 1_000_000;
                String get = redis.get("idem:250000");               // a lazy check on one key
                System.out.printf("t=%5d ms  GET idem:250000 -> %-6s DBSIZE %,7d  expired %,7d  used_memory %3d MB%n",
                        ms, get, redis.dbSize(), stat(redis, "expired_keys") - expiredBefore, stat(redis, "used_memory") / 1_000_000);
                Thread.sleep(150);
            }
        }
    }

    static long stat(RedisClient redis, String field) {
        String section = field.startsWith("used_memory") ? "memory" : "stats";
        for (String line : redis.info(section).split("\r\n")) {
            if (line.startsWith(field + ":")) return Long.parseLong(line.substring(field.length() + 1).trim());
        }
        throw new IllegalArgumentException(field);
    }
}
