package sfz.msg.l01;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Reads a consumer's processing log and says what happened to per-key order. */
public final class OrderCheck {
    private OrderCheck() {}

    /**
     * @param processed  how many entries the log has, duplicates included
     * @param duplicates entries whose message (same key, same seq) was already processed earlier in the log
     * @param inversions first-time entries whose seq is lower than the highest seq already processed for the same key
     */
    public record Result(int processed, int duplicates, int inversions) {}

    /**
     * Walks {@code processed}, the messages in the order consumers finished them, and counts duplicates and
     * inversions as {@link Result} defines them. {@code m1 m2 m4 m3 m5} for one key has one inversion (m3);
     * {@code m1 m2 m2 m3} has one duplicate and no inversion. Keys never affect each other.
     */
    public static Result check(List<Message> processed) {
        Set<Message> seen = new HashSet<>();               // Message is a Kotlin data class: equal by key and seq
        Map<String, Integer> highest = new HashMap<>();    // key -> highest seq processed so far
        int duplicates = 0;
        int inversions = 0;
        for (Message m : processed) {
            if (!seen.add(m)) {                            // processed before: a redelivery after a lost ack
                duplicates++;
                continue;
            }
            Integer top = highest.get(m.getKey());
            if (top != null && m.getSeq() < top) {
                inversions++;                              // a later message of this key was processed first
            } else {
                highest.put(m.getKey(), m.getSeq());       // never lower the high mark
            }
        }
        return new Result(processed.size(), duplicates, inversions);
    }
}
