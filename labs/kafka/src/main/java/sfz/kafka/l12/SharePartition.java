package sfz.kafka.l12;

import org.apache.kafka.clients.consumer.AcknowledgeType;

import java.util.ArrayList;
import java.util.List;

/**
 * One partition as a share group sees it: a model of the broker's share-partition. Every record has a state, a
 * delivery count and, while a consumer holds it, a lock that runs out.
 *
 * <pre>
 *   AVAILABLE --acquire--> ACQUIRED --ACCEPT--> ACKNOWLEDGED
 *       ^                     |  |
 *       +--RELEASE or lock ---+  +--REJECT, or RELEASE / lock expiry at the delivery limit--> ARCHIVED
 *          expiry (below the limit)
 * </pre>
 *
 * Time is passed in ({@code nowMs}) so that tests control the clock.
 */
public final class SharePartition {
    public enum State { AVAILABLE, ACQUIRED, ACKNOWLEDGED, ARCHIVED }

    /** One record handed to a consumer: its offset and how many times it has been delivered, this time included. */
    public record Delivery(long offset, int deliveryCount) {
    }

    private static final class Slot {
        State state = State.AVAILABLE;
        int deliveries;
        String owner;
        long lockedUntil;
    }

    private final int deliveryLimit;
    private final long lockDurationMs;
    private final int maxRecordLocks;
    private final List<Slot> slots = new ArrayList<>();   // index = offset

    /**
     * @param deliveryLimit  {@code share.delivery.count.limit}: deliveries before a record is archived (default 5)
     * @param lockDurationMs {@code share.record.lock.duration.ms}: how long an acquired record stays locked (default 30 s)
     * @param maxRecordLocks how many records may be ACQUIRED at once; a simplification of
     *                       {@code share.partition.max.record.locks} (default 2000)
     */
    public SharePartition(int deliveryLimit, long lockDurationMs, int maxRecordLocks) {
        this.deliveryLimit = deliveryLimit;
        this.lockDurationMs = lockDurationMs;
        this.maxRecordLocks = maxRecordLocks;
    }

    /** A producer appended {@code records} more records at the end of the partition. They start AVAILABLE. */
    public void append(int records) {
        for (int i = 0; i < records; i++) slots.add(new Slot());
    }

    public State state(long offset) {
        return slots.get((int) offset).state;
    }

    public int deliveryCount(long offset) {
        return slots.get((int) offset).deliveries;
    }

    /**
     * Ends every lock that has run out by {@code nowMs} (its end time is at or before {@code nowMs}): the record
     * goes back to AVAILABLE, or to ARCHIVED if it has already been delivered {@code deliveryLimit} times.
     */
    private void expireLocks(long nowMs) {
        throw new UnsupportedOperationException("TODO: ACQUIRED records whose lock ended go back to AVAILABLE, or to ARCHIVED at the limit");
    }

    /**
     * A share fetch from {@code consumer}. First end the locks that have run out. Then hand out AVAILABLE records in
     * offset order, at most {@code maxRecords} of them, and never so many that more than {@code maxRecordLocks}
     * records are ACQUIRED at once. Each one handed out becomes ACQUIRED by {@code consumer}, locked until
     * {@code nowMs + lockDurationMs}, with its delivery count one higher.
     */
    public List<Delivery> acquire(String consumer, int maxRecords, long nowMs) {
        throw new UnsupportedOperationException("TODO: expire locks, then hand out AVAILABLE records in offset order within both limits");
    }

    /**
     * {@code consumer} acknowledges one record. First end the locks that have run out. The record must then be
     * ACQUIRED by this consumer, or the acknowledgement is refused with an {@link IllegalStateException} (its lock ran
     * out, or another consumer holds it).
     *
     * <ul>
     *   <li>ACCEPT: done, ACKNOWLEDGED.</li>
     *   <li>RELEASE: AVAILABLE again for any consumer, unless it has been delivered {@code deliveryLimit} times:
     *       then ARCHIVED.</li>
     *   <li>REJECT: ARCHIVED, never delivered again.</li>
     *   <li>RENEW: still ACQUIRED by this consumer, with its lock extended to {@code nowMs + lockDurationMs}.</li>
     * </ul>
     */
    public void acknowledge(String consumer, long offset, AcknowledgeType type, long nowMs) {
        throw new UnsupportedOperationException("TODO: expire locks, check the owner, then ACCEPT, RELEASE, REJECT or RENEW");
    }

    /**
     * The share-partition start offset: the lowest offset that is neither ACKNOWLEDGED nor ARCHIVED (every record
     * before it is finished), or the end of the partition if all are.
     */
    public long startOffset() {
        throw new UnsupportedOperationException("TODO: the lowest offset that is not finished");
    }
}
