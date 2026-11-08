package sfz.cache.l01;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;

public final class LruCache<K> {
    private final int capacity;
    private final LinkedHashMap<K, Boolean> entries;
    private long hits;
    private long misses;
    private long evictions;

    public LruCache(int capacity) {
        if (capacity < 1) throw new IllegalArgumentException("capacity must be at least 1");
        this.capacity = capacity;
        this.entries = new LinkedHashMap<>(16, 0.75f, true);
    }

    public boolean access(K key) {
        if (entries.get(key) != null) {               // get() on an access-ordered map moves the key to the newest end
            hits++;
            return true;
        }
        misses++;
        if (entries.size() >= capacity) {             // full: the oldest key is first in iteration order
            K oldest = entries.keySet().iterator().next();
            entries.remove(oldest);
            evictions++;
        }
        entries.put(key, Boolean.TRUE);               // a new key starts as the most recently used
        return false;
    }

    public boolean contains(K key) {
        return entries.containsKey(key);
    }

    public int size() {
        return entries.size();
    }

    public int capacity() {
        return capacity;
    }

    public List<K> keysOldestFirst() {
        return new ArrayList<>(entries.keySet());
    }

    public long hits() {
        return hits;
    }

    public long misses() {
        return misses;
    }

    public long evictions() {
        return evictions;
    }

    public double missRatio() {
        long total = hits + misses;
        return total == 0 ? 0.0 : (double) misses / total;
    }

    public void resetStats() {
        hits = 0;
        misses = 0;
        evictions = 0;
    }
}
