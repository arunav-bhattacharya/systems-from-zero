package sfz.cache.l01.demo;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Random;

/** LRU miss-ratio curves for Zipf traffic over 100,000 keys, and the loop that defeats LRU. */
public class MissRatioDemo {
    public static void main(String[] args) {
        int n = 100_000;
        int[] sizes = {100, 1_000, 10_000, 50_000};        // 0.1%, 1%, 10% and 50% of the keys
        System.out.println("LRU miss ratio, 1,000,000 requests over 100,000 keys");
        System.out.println("alpha    100 keys  1,000 keys  10,000 keys  50,000 keys");
        for (double alpha : new double[] {0.8, 1.0, 1.2}) {
            int[] trace = zipfTrace(n, alpha, 1_000_000, 7);
            StringBuilder row = new StringBuilder(String.format("%5.1f", alpha));
            for (int size : sizes) row.append(String.format("  %10.1f%%", 100 * lruMissRatio(trace, size, 200_000)));
            System.out.println(row);
        }
        for (int keys : new int[] {1_001, 2_000}) {
            int[] loop = new int[keys * 50];               // keys 1..n, over and over
            for (int i = 0; i < loop.length; i++) loop[i] = i % keys + 1;
            System.out.printf("loop over %,d keys: cache of 1,000 misses %.0f%%, cache of %,d misses %.0f%%%n",
                    keys, 100 * lruMissRatio(loop, 1_000, keys), keys, 100 * lruMissRatio(loop, keys, keys));
        }
    }

    /** Replays the trace through an LRU cache of {@code size} keys; the first {@code warmup} requests aren't counted. */
    static double lruMissRatio(int[] trace, int size, int warmup) {
        Map<Integer, Boolean> lru = new LinkedHashMap<>(16, 0.75f, true) {
            @Override protected boolean removeEldestEntry(Map.Entry<Integer, Boolean> eldest) {
                return size() > size;                      // evict the least recently used key
            }
        };
        long misses = 0;
        for (int i = 0; i < trace.length; i++) {
            if (lru.get(trace[i]) == null) {               // get() also marks the key as just used
                lru.put(trace[i], Boolean.TRUE);
                if (i >= warmup) misses++;
            }
        }
        return (double) misses / (trace.length - warmup);
    }

    static int[] zipfTrace(int n, double alpha, int length, long seed) {
        double[] cdf = new double[n];
        double total = 0;
        for (int k = 1; k <= n; k++) total += Math.pow(k, -alpha);
        double running = 0;
        for (int k = 1; k <= n; k++) { running += Math.pow(k, -alpha) / total; cdf[k - 1] = running; }
        cdf[n - 1] = 1.0;
        Random random = new Random(seed);
        int[] trace = new int[length];
        for (int i = 0; i < length; i++) {
            int k = Arrays.binarySearch(cdf, random.nextDouble());
            trace[i] = (k >= 0 ? k : -k - 1) + 1;
        }
        return trace;
    }
}
