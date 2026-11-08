package sfz.cache.l01;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;

/**
 * A cache of at most {@code capacity} keys that evicts the least recently used one: LRU.
 *
 * <p>It stores only keys, because this lab measures hits and misses, not values. The storage is a
 * {@link LinkedHashMap} built in <em>access order</em> (the {@code true} in its constructor). Such a
 * map keeps its keys in a list from least to most recently used, and two calls move a key to the
 * newest end of that list: {@code get} and {@code put}. {@code containsKey} does not move anything.
 * So the first key in iteration order, {@code entries.keySet().iterator().next()}, is always the
 * least recently used one.
 */
public final class LruCache<K> {
    private final int capacity;
    private final LinkedHashMap<K, Boolean> entries;
    private long hits;
    private long misses;
    private long evictions;

    /** An empty cache that holds at most {@code capacity} keys. */
    public LruCache(int capacity) {
        if (capacity < 1) throw new IllegalArgumentException("capacity must be at least 1");
        this.capacity = capacity;
        this.entries = new LinkedHashMap<>(16, 0.75f, true);
    }

    /**
     * One request for {@code key}. Returns true on a hit, false on a miss.
     *
     * <ol>
     *   <li>A hit: the key is cached. Make it the most recently used ({@code get} does that),
     *       count a hit and return true.</li>
     *   <li>A miss: count a miss. If the cache already holds {@code capacity} keys, remove the least
     *       recently used key and count an eviction. Then {@code put} the key (value
     *       {@code Boolean.TRUE}) and return false.</li>
     * </ol>
     */
    public boolean access(K key) {
        throw new UnsupportedOperationException("TODO: lesson 1 lab: a hit moves the key to the newest end; a miss evicts the oldest if full, then inserts");
    }

    /** True if {@code key} is cached. Doesn't count as a use. Done for you. */
    public boolean contains(K key) {
        return entries.containsKey(key);
    }

    /** How many keys are cached. Done for you. */
    public int size() {
        return entries.size();
    }

    /** The most keys this cache holds. Done for you. */
    public int capacity() {
        return capacity;
    }

    /** The cached keys, least recently used first. Done for you. */
    public List<K> keysOldestFirst() {
        return new ArrayList<>(entries.keySet());
    }

    /** Hits since the start or the last {@link #resetStats()}. Done for you. */
    public long hits() {
        return hits;
    }

    /** Misses since the start or the last {@link #resetStats()}. Done for you. */
    public long misses() {
        return misses;
    }

    /** Evictions since the start or the last {@link #resetStats()}. Done for you. */
    public long evictions() {
        return evictions;
    }

    /** misses / (hits + misses), or 0 before the first request. Done for you. */
    public double missRatio() {
        long total = hits + misses;
        return total == 0 ? 0.0 : (double) misses / total;
    }

    /** Zeroes the counters but keeps the cached keys, for example after a warm-up. Done for you. */
    public void resetStats() {
        hits = 0;
        misses = 0;
        evictions = 0;
    }
}
