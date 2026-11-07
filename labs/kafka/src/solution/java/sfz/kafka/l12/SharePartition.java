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
        for (Slot s : slots) {
            if (s.state == State.ACQUIRED && s.lockedUntil <= nowMs) {
                s.state = s.deliveries >= deliveryLimit ? State.ARCHIVED : State.AVAILABLE;   // the lock ran out
                s.owner = null;
            }
        }
    }

    /**
     * A share fetch from {@code consumer}. First end the locks that have run out. Then hand out AVAILABLE records in
     * offset order, at most {@code maxRecords} of them, and never so many that more than {@code maxRecordLocks}
     * records are ACQUIRED at once. Each one handed out becomes ACQUIRED by {@code consumer}, locked until
     * {@code nowMs + lockDurationMs}, with its delivery count one higher.
     */
    public List<Delivery> acquire(String consumer, int maxRecords, long nowMs) {
        expireLocks(nowMs);
        int locked = (int) slots.stream().filter(s -> s.state == State.ACQUIRED).count();
        List<Delivery> out = new ArrayList<>();
        for (int offset = (int) startOffset(); offset < slots.size(); offset++) {
            if (out.size() == maxRecords || locked == maxRecordLocks) break;
            Slot s = slots.get(offset);
            if (s.state != State.AVAILABLE) continue;            // held by someone else, or finished
            s.state = State.ACQUIRED;
            s.owner = consumer;
            s.lockedUntil = nowMs + lockDurationMs;
            s.deliveries++;                                       // counted when handed out, not when acknowledged
            locked++;
            out.add(new Delivery(offset, s.deliveries));
        }
        return out;
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
        expireLocks(nowMs);
        Slot s = slots.get((int) offset);
        if (s.state != State.ACQUIRED || !consumer.equals(s.owner))
            throw new IllegalStateException("offset " + offset + " is not acquired by " + consumer + " (" + s.state + ")");
        switch (type) {
            case ACCEPT -> s.state = State.ACKNOWLEDGED;
            case RELEASE -> s.state = s.deliveries >= deliveryLimit ? State.ARCHIVED : State.AVAILABLE;
            case REJECT -> s.state = State.ARCHIVED;
            case RENEW -> s.lockedUntil = nowMs + lockDurationMs;  // more time, same owner, same delivery count
        }
        if (s.state != State.ACQUIRED) s.owner = null;
    }

    /**
     * The share-partition start offset: the lowest offset that is neither ACKNOWLEDGED nor ARCHIVED (every record
     * before it is finished), or the end of the partition if all are.
     */
    public long startOffset() {
        for (int offset = 0; offset < slots.size(); offset++) {
            State st = slots.get(offset).state;
            if (st != State.ACKNOWLEDGED && st != State.ARCHIVED) return offset;
        }
        return slots.size();
    }
}
