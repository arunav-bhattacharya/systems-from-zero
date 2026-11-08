package sfz.cache.l05;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * A cache of at most {@code capacity} keys that evicts the way Redis does under {@code allkeys-lru}.
 *
 * <p>Exact LRU would keep every key in a list ordered by last use and move a key to the front on
 * every access. Redis doesn't. It stamps each key with the time of its last use, and when it must
 * evict, it looks at a few keys picked at random ({@code maxmemory-samples}, 5 by default) and evicts
 * the one with the oldest stamp.
 *
 * <p>This model uses a logical clock: every call to {@link #access} is one tick. The storage is done
 * for you: {@code keys} holds every key in a list, so a random key is one random index away, and
 * {@code lastUsed} holds each key's stamp. Use {@link #insert} and {@link #remove} to change them.
 */
public final class SampledLru {
    private final int capacity;
    private final int samples;
    private final Random random;

    private final List<String> keys = new ArrayList<>();
    private final Map<String, Integer> slot = new HashMap<>();
    private final Map<String, Long> lastUsed = new HashMap<>();
    private long clock;
    private long evictions;

    /** A cache for {@code capacity} keys that looks at {@code samples} keys per eviction. {@code seed} makes runs repeatable. */
    public SampledLru(int capacity, int samples, long seed) {
        if (capacity < 1 || samples < 1) throw new IllegalArgumentException("capacity and samples must be at least 1");
        this.capacity = capacity;
        this.samples = samples;
        this.random = new Random(seed);
    }

    /**
     * Reads or writes {@code key}. Returns true if it was already cached (a hit), false if not (a miss).
     *
     * <ol>
     *   <li>Tick the clock: {@code clock++}.</li>
     *   <li>A hit: stamp the key with the new clock value and return true.</li>
     *   <li>A miss: if the cache is full, remove {@link #chooseVictim()} and count one eviction.
     *       Then {@link #insert} the key and return false.</li>
     * </ol>
     */
    public boolean access(String key) {
        throw new UnsupportedOperationException("TODO: tick, stamp a hit, or evict and insert on a miss");
    }

    /**
     * The key to evict. Look at {@code samples} keys picked with {@code keys.get(random.nextInt(keys.size()))}
     * and return the one with the smallest {@code lastUsed} stamp. If {@code samples} is at least the
     * number of keys, look at every key instead: that is exact LRU.
     */
    public String chooseVictim() {
        throw new UnsupportedOperationException("TODO: sample a few keys, return the least recently used");
    }

    /** True if {@code key} is cached. Done for you. */
    public boolean contains(String key) {
        return lastUsed.containsKey(key);
    }

    /** How many keys are cached. Done for you. */
    public int size() {
        return keys.size();
    }

    /** How many keys have been evicted so far. Done for you. */
    public long evictions() {
        return evictions;
    }

    /** The clock value of the key's last access. Done for you. */
    public long lastUsed(String key) {
        Long t = lastUsed.get(key);
        if (t == null) throw new IllegalArgumentException("no such key: " + key);
        return t;
    }

    /** Adds a key that is not cached yet, stamped with the current clock. Done for you. */
    private void insert(String key) {
        slot.put(key, keys.size());
        keys.add(key);
        lastUsed.put(key, clock);
    }

    /** Removes a cached key in O(1): the last key in the list moves into its place. Done for you. */
    private void remove(String key) {
        int i = slot.remove(key);
        String last = keys.remove(keys.size() - 1);
        if (i < keys.size()) {
            keys.set(i, last);
            slot.put(last, i);
        }
        lastUsed.remove(key);
    }
}
