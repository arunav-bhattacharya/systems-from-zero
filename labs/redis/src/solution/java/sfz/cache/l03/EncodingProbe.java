package sfz.cache.l03;

import redis.clients.jedis.RedisClient;

import java.util.function.IntConsumer;

public final class EncodingProbe {

    public record Snapshot(String encoding, long bytes) {}

    public record Transition(String from, String to, int atSize, long bytesBefore, long bytesAfter) {}

    private EncodingProbe() {}

    public static Snapshot describe(RedisClient redis, String key) {
        // two round trips; MEMORY USAGE samples 5 elements of a big key and extrapolates
        return new Snapshot(redis.objectEncoding(key), redis.memoryUsage(key));
    }

    public static Transition growUntilConverted(RedisClient redis, String key, int maxSize, IntConsumer addOne) {
        addOne.accept(1);                              // the first add creates the key
        Snapshot before = describe(redis, key);
        for (int i = 2; i <= maxSize; i++) {
            addOne.accept(i);
            Snapshot after = describe(redis, key);
            if (!after.encoding().equals(before.encoding())) {
                return new Transition(before.encoding(), after.encoding(), i, before.bytes(), after.bytes());
            }
            before = after;
        }
        return null;                                   // still the same encoding at maxSize
    }
}
