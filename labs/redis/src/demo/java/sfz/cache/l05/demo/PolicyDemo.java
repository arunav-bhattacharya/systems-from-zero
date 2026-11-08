package sfz.cache.l05.demo;

import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/** FIFO, LRU and SIEVE on the same Zipf requests, without and with one-time scans mixed in. No Docker needed. */
public class PolicyDemo {
    interface Policy { boolean access(int key); }

    public static void main(String[] args) {
        int n = 100_000;
        int[] zipf = zipfTrace(n, 1.0, 1_000_000, 7);
        int[] scans = withScans(zipf, n);
        System.out.println("miss ratio on the Zipf requests (alpha 1.0, 100,000 keys)");
        System.out.println("cache     workload        FIFO     LRU   SIEVE");
        for (int size : new int[] {1_000, 10_000}) {
            for (int[] trace : new int[][] {zipf, scans}) {
                System.out.printf("%,6d    %-12s  %6.1f%%  %5.1f%%  %5.1f%%%n", size, trace == zipf ? "Zipf" : "Zipf + scans",
                        100 * missRatio(trace, new Fifo(size), n), 100 * missRatio(trace, new Lru(size), n),
                        100 * missRatio(trace, new Sieve(size), n));
            }
        }
    }

    /** Misses among the Zipf requests after a warm-up; scan keys (above n) are replayed but not counted. */
    static double missRatio(int[] trace, Policy policy, int n) {
        long counted = 0, misses = 0;
        for (int i = 0; i < trace.length; i++) {
            boolean hit = policy.access(trace[i]);
            if (i >= trace.length / 5 && trace[i] <= n) {
                counted++;
                if (!hit) misses++;
            }
        }
        return (double) misses / counted;
    }

    /** FIFO: evict the key that was inserted first; a hit changes nothing. */
    static final class Fifo implements Policy {
        final int capacity;
        final ArrayDeque<Integer> queue = new ArrayDeque<>();
        final Set<Integer> cached = new HashSet<>();
        Fifo(int capacity) { this.capacity = capacity; }
        public boolean access(int key) {
            if (cached.contains(key)) return true;
            if (cached.size() >= capacity) cached.remove(queue.pollFirst());
            queue.addLast(key);
            cached.add(key);
            return false;
        }
    }

    /** LRU: a hit moves the key to the newest end; evict from the oldest end. */
    static final class Lru implements Policy {
        final Map<Integer, Boolean> map;
        Lru(int capacity) {
            map = new LinkedHashMap<>(16, 0.75f, true) {
                @Override protected boolean removeEldestEntry(Map.Entry<Integer, Boolean> eldest) { return size() > capacity; }
            };
        }
        public boolean access(int key) {
            if (map.get(key) != null) return true;
            map.put(key, Boolean.TRUE);
            return false;
        }
    }

    /** SIEVE: one FIFO list and a visited bit. A hit only sets the bit; the hand evicts the first unvisited key. */
    static final class Sieve implements Policy {
        static final class Node {
            final int key;
            boolean visited;
            Node newer, older;
            Node(int key) { this.key = key; }
        }
        final int capacity;
        final Map<Integer, Node> nodes = new HashMap<>();
        Node head, tail, hand;                              // head: newest, tail: oldest

        Sieve(int capacity) { this.capacity = capacity; }

        public boolean access(int key) {
            Node node = nodes.get(key);
            if (node != null) {
                node.visited = true;                        // no move, no lock needed in a concurrent version
                return true;
            }
            if (nodes.size() >= capacity) evict();
            node = new Node(key);                           // new keys always enter at the head
            node.older = head;
            if (head != null) head.newer = node;
            head = node;
            if (tail == null) tail = node;
            nodes.put(key, node);
            return false;
        }

        void evict() {
            Node o = hand != null ? hand : tail;
            while (o.visited) {                             // spare visited keys, clear their bit, keep walking
                o.visited = false;
                o = o.newer != null ? o.newer : tail;       // past the head: start again from the tail
            }
            hand = o.newer;                                 // the next eviction resumes here
            if (o.newer != null) o.newer.older = o.older; else head = o.older;
            if (o.older != null) o.older.newer = o.newer; else tail = o.newer;
            nodes.remove(o.key);
        }
    }

    /** After every 50,000 requests, a one-time scan of 5,000 keys nobody asks for again. */
    static int[] withScans(int[] zipf, int n) {
        int[] out = new int[zipf.length + zipf.length / 50_000 * 5_000];
        int next = n + 1, j = 0;
        for (int i = 0; i < zipf.length; i++) {
            out[j++] = zipf[i];
            if ((i + 1) % 50_000 == 0) for (int s = 0; s < 5_000; s++) out[j++] = next++;
        }
        return out;
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
