package sfz.msg.l05;

import java.nio.charset.StandardCharsets;

/**
 * The producer's default rule for records that have a key, written out by hand:
 * partition = toPositive(murmur2(key bytes)) % numPartitions.
 * It is the same arithmetic as {@code BuiltInPartitioner.partitionForKey} in kafka-clients 4.4.
 */
public final class KeyPartitioner {
    private KeyPartitioner() {}

    /**
     * MurmurHash2, 32-bit, with Kafka's seed. Given: it is the same algorithm as Kafka's {@code Utils.murmur2}.
     * It mixes every byte of the key into one int, so similar keys ("acct-17", "acct-18") get unrelated hashes.
     * The result is negative about half the time.
     */
    public static int murmur2(byte[] data) {
        final int m = 0x5bd1e995; // mixing constants from the original MurmurHash2
        final int r = 24;
        int length = data.length;
        int h = 0x9747b28c ^ length; // Kafka's seed, mixed with the length

        // mix four bytes at a time, read little-endian
        int whole = length / 4;
        for (int i = 0; i < whole; i++) {
            int j = i * 4;
            int k = (data[j] & 0xff)
                    | (data[j + 1] & 0xff) << 8
                    | (data[j + 2] & 0xff) << 16
                    | (data[j + 3] & 0xff) << 24;
            k *= m;
            k ^= k >>> r;
            k *= m;
            h *= m;
            h ^= k;
        }

        // mix the last one to three bytes
        int tail = whole * 4;
        switch (length % 4) {
            case 3:
                h ^= (data[tail + 2] & 0xff) << 16;
            case 2: // falls through
                h ^= (data[tail + 1] & 0xff) << 8;
            case 1: // falls through
                h ^= data[tail] & 0xff;
                h *= m;
            default:
                break;
        }

        // final avalanche, so every input bit affects every output bit
        h ^= h >>> 13;
        h *= m;
        h ^= h >>> 15;
        return h;
    }

    /** Clears the sign bit, so the result is never negative: 7 stays 7, -1 becomes 2147483647. */
    public static int toPositive(int number) {
        // Math.abs would be wrong: Math.abs(Integer.MIN_VALUE) is still negative
        return number & 0x7fffffff;
    }

    /** The partition the default partitioner picks for this String key, given the topic's partition count. */
    public static int partitionFor(String key, int numPartitions) {
        // StringSerializer sends UTF-8, and the producer hashes the serialized bytes, not the String
        byte[] bytes = key.getBytes(StandardCharsets.UTF_8);
        return toPositive(murmur2(bytes)) % numPartitions;
    }
}
