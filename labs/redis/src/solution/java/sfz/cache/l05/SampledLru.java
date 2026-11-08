package sfz.cache.l05;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

public final class SampledLru {
    private final int capacity;
    private final int samples;
    private final Random random;

    private final List<String> keys = new ArrayList<>();
    private final Map<String, Integer> slot = new HashMap<>();
    private final Map<String, Long> lastUsed = new HashMap<>();
    private long clock;
    private long evictions;

    public SampledLru(int capacity, int samples, long seed) {
        if (capacity < 1 || samples < 1) throw new IllegalArgumentException("capacity and samples must be at least 1");
        this.capacity = capacity;
        this.samples = samples;
        this.random = new Random(seed);
    }

    public boolean access(String key) {
        clock++;                                       // every access is one tick of the logical clock
        if (lastUsed.containsKey(key)) {
            lastUsed.put(key, clock);                  // a hit refreshes the stamp: the key is young again
            return true;
        }
        if (keys.size() >= capacity) {                 // full: make room first, as Redis does before a write
            remove(chooseVictim());
            evictions++;
        }
        insert(key);
        return false;
    }

    public String chooseVictim() {
        if (keys.isEmpty()) throw new IllegalStateException("nothing to evict");
        if (samples >= keys.size()) {                  // the sample covers everything: exact LRU
            String oldest = keys.get(0);
            for (String k : keys) if (lastUsed.get(k) < lastUsed.get(oldest)) oldest = k;
            return oldest;
        }
        String victim = null;
        for (int i = 0; i < samples; i++) {            // a few random keys, the oldest of them loses
            String candidate = keys.get(random.nextInt(keys.size()));
            if (victim == null || lastUsed.get(candidate) < lastUsed.get(victim)) victim = candidate;
        }
        return victim;
    }

    public boolean contains(String key) {
        return lastUsed.containsKey(key);
    }

    public int size() {
        return keys.size();
    }

    public long evictions() {
        return evictions;
    }

    public long lastUsed(String key) {
        Long t = lastUsed.get(key);
        if (t == null) throw new IllegalArgumentException("no such key: " + key);
        return t;
    }

    private void insert(String key) {
        slot.put(key, keys.size());
        keys.add(key);
        lastUsed.put(key, clock);
    }

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
