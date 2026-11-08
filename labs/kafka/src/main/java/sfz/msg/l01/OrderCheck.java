package sfz.msg.l01;

import java.util.List;

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
        throw new UnsupportedOperationException(
                "TODO: one pass; a Set<Message> for duplicates and a Map<String, Integer> of the highest seq per key");
    }
}
