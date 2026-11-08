package sfz.cache.l03;

import redis.clients.jedis.RedisClient;

import java.util.function.IntConsumer;

/**
 * Watches Redis change a key's internal encoding as the key grows.
 *
 * <p>Two commands do the looking: {@code OBJECT ENCODING key} names the encoding
 * ({@code listpack}, {@code intset}, {@code skiplist}, {@code hashtable}, ...), and
 * {@code MEMORY USAGE key} estimates the bytes the key takes, value and overhead included.
 */
public final class EncodingProbe {

    /** How a key is stored right now. */
    public record Snapshot(String encoding, long bytes) {}

    /**
     * The first change of encoding seen while a key grew.
     *
     * @param from        the encoding before the add that changed it
     * @param to          the encoding after it
     * @param atSize      how many elements the key held after that add (the add was element number atSize)
     * @param bytesBefore MEMORY USAGE just before the change
     * @param bytesAfter  MEMORY USAGE just after it
     */
    public record Transition(String from, String to, int atSize, long bytesBefore, long bytesAfter) {}

    private EncodingProbe() {}

    /** OBJECT ENCODING and MEMORY USAGE of {@code key}. Jedis: {@code objectEncoding(key)} and {@code memoryUsage(key)}. */
    public static Snapshot describe(RedisClient redis, String key) {
        throw new UnsupportedOperationException("TODO: read OBJECT ENCODING and MEMORY USAGE");
    }

    /**
     * Grows {@code key} one element at a time and reports the first change of encoding.
     *
     * <p>{@code addOne.accept(i)} adds element number i to the key (call it with i = 1, 2, 3, ...).
     * Take a {@link #describe snapshot} after every add. As soon as the encoding differs from the
     * snapshot before that add, return the {@link Transition}. Return {@code null} if the encoding
     * never changes within {@code maxSize} adds.
     */
    public static Transition growUntilConverted(RedisClient redis, String key, int maxSize, IntConsumer addOne) {
        throw new UnsupportedOperationException("TODO: add, describe, compare, repeat");
    }
}
