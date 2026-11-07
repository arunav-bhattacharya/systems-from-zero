package sfz.redis.l03;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/**
 * A small HyperLogLog, built the way Redis builds its own (Redis uses p = 14).
 *
 * <p>There are m = 2^p registers of one byte each. To add an element, hash it to 64 bits. The low
 * p bits pick a register. In the remaining bits, count the zero bits before the first 1 bit,
 * starting from the lowest bit, and add 1: that is the element's rank. The register keeps the
 * largest rank it has ever seen. Registers never go down, and adding the same element twice
 * changes nothing.
 */
public final class TinyHyperLogLog {
    private final int p;
    private final byte[] registers;

    /** A counter with 2^p registers, for p between 4 and 16. */
    public TinyHyperLogLog(int p) {
        if (p < 4 || p > 16) throw new IllegalArgumentException("p must be 4..16");
        this.p = p;
        this.registers = new byte[1 << p];
    }

    /** How many index bits this counter uses. */
    public int p() {
        return p;
    }

    /** A copy of the registers, for tests and for printing. */
    public byte[] registers() {
        return Arrays.copyOf(registers, registers.length);
    }

    /**
     * Adds one element. Returns true if a register changed (as PFADD returns 1), false otherwise.
     *
     * <ol>
     *   <li>{@code long h = hash64(element)}</li>
     *   <li>index: the low p bits of h</li>
     *   <li>rank: shift h right by p, then count trailing zero bits and add 1. Before counting, set bit
     *       (64 - p) of the shifted value, so an all-zero rest still gives a rank of at most 65 - p.</li>
     *   <li>keep the larger of the register and the rank</li>
     * </ol>
     */
    public boolean add(String element) {
        throw new UnsupportedOperationException("TODO: hash, pick a register, count zeros, keep the max");
    }

    /**
     * Folds {@code other} into this counter, so it estimates the union of both sets of elements.
     * Both must have the same p. This is what PFMERGE does.
     */
    public void merge(TinyHyperLogLog other) {
        throw new UnsupportedOperationException("TODO: register by register, keep the max");
    }

    /**
     * The estimated number of distinct elements added. Done for you: the classic HyperLogLog
     * estimate (a harmonic mean of 2^register), with linear counting while many registers are 0.
     */
    public long estimate() {
        int m = registers.length;
        double sum = 0;
        int zeros = 0;
        for (byte r : registers) {
            sum += Math.pow(2, -r);
            if (r == 0) zeros++;
        }
        double alpha = 0.7213 / (1 + 1.079 / m);
        double e = alpha * m * m / sum;
        if (e <= 2.5 * m && zeros > 0) {
            e = m * Math.log((double) m / zeros);   // small counts: count the empty registers instead
        }
        return Math.round(e);
    }

    /** A 64-bit hash with well-mixed bits: FNV-1a over the UTF-8 bytes, then a final mix. Done for you. */
    public static long hash64(String s) {
        long h = 0xcbf29ce484222325L;
        for (byte b : s.getBytes(StandardCharsets.UTF_8)) {
            h ^= (b & 0xff);
            h *= 0x100000001b3L;
        }
        h ^= h >>> 33;
        h *= 0xff51afd7ed558ccdL;
        h ^= h >>> 33;
        h *= 0xc4ceb9fe1a85ec53L;
        h ^= h >>> 33;
        return h;
    }
}
