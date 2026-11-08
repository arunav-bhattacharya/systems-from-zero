package sfz.msg.l03;

import java.util.List;

/** Log compaction, the job of the broker's log cleaner on a topic with {@code cleanup.policy=compact}. */
public final class Compaction {
    private Compaction() {}

    /**
     * Compacts the records of a log's closed segments and returns the records that survive.
     *
     * <p>The input is oldest first, and every record has a key (Kafka rejects records without a key on a
     * compacted topic). The active segment is never part of the input: the cleaner leaves it alone.
     *
     * <ol>
     *   <li>For each key, keep only its last record: the one with the highest offset. Drop the older ones.</li>
     *   <li>Keep the survivors in their original order, with their original offsets. The gaps are fine:
     *       a reader that asks for a missing offset just gets the next record that exists.</li>
     *   <li>A tombstone ({@code value == null}) that is the last record for its key stays, so that every
     *       consumer gets to see the delete. Drop it once {@code nowMs - timestampMs > deleteRetentionMs}.</li>
     * </ol>
     *
     * Do not change the input list. (Use {@link Rec#getKey()}, {@link Rec#getValue()}, {@link Rec#getOffset()}
     * and {@link Rec#getTimestampMs()}: {@code Rec} is a Kotlin data class.)
     */
    public static List<Rec> compact(List<Rec> closed, long nowMs, long deleteRetentionMs) {
        throw new UnsupportedOperationException("TODO: find each key's last offset, then keep only those records");
    }
}
