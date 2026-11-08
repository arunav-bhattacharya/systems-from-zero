package sfz.msg.l06;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * One partition's log on the leader, with the duplicate check an idempotent producer relies on.
 *
 * <p>Every idempotent producer has a producer id. It numbers the records it sends to each partition 0, 1, 2, ...
 * and every batch carries the number of its first record, the base sequence. A batch of 3 records with base
 * sequence 10 holds sequences 10, 11 and 12. For each producer the leader remembers the next sequence it
 * expects and the last {@value #BATCHES_TO_RETAIN} batches it appended (Kafka's
 * {@code ProducerStateEntry.NUM_BATCHES_TO_RETAIN} is 5, which is why idempotence needs
 * {@code max.in.flight.requests.per.connection <= 5}).
 */
public final class IdempotentLog {

    /** How many recent batches the leader remembers per producer. */
    public static final int BATCHES_TO_RETAIN = 5;

    /** What the leader answers. */
    public sealed interface Result permits Appended, Duplicate, OutOfOrder {}

    /** The batch was written; its first record got {@code baseOffset}. */
    public record Appended(long baseOffset) implements Result {}

    /** The batch was written before, at {@code baseOffset}. Nothing was written now; the producer treats this as success. */
    public record Duplicate(long baseOffset) implements Result {}

    /** The batch does not start at the sequence the leader expects next. Nothing was written. */
    public record OutOfOrder(int expectedSequence) implements Result {}

    /** A batch the leader remembers: its first and last sequence and where it was written. */
    private record BatchInfo(int firstSeq, int lastSeq, long baseOffset) {}

    /** What the leader knows about one producer. */
    private static final class ProducerState {
        int nextSeq = 0;                                    // a new producer must start at sequence 0
        final Deque<BatchInfo> recent = new ArrayDeque<>(); // oldest first, at most BATCHES_TO_RETAIN
    }

    private final List<String> log = new ArrayList<>();
    private final Map<Long, ProducerState> producers = new HashMap<>();

    /** Everything written so far, in offset order. */
    public List<String> records() {
        return Collections.unmodifiableList(log);
    }

    /**
     * The leader receives a batch of {@code records} from {@code producerId} whose first record has sequence
     * {@code baseSequence}.
     *
     * <ol>
     *   <li>If the producer's remembered batches include one with the same first and last sequence, it is a
     *       retry of a batch already written: return {@link Duplicate} with that batch's base offset.</li>
     *   <li>If {@code baseSequence} is the sequence the leader expects next, append the records, remember the batch
     *       (forget the oldest beyond {@link #BATCHES_TO_RETAIN}), move the expected sequence past the batch and
     *       return {@link Appended} with the offset of its first record.</li>
     *   <li>Anything else is a gap, or a retry too old to recognise: return {@link OutOfOrder} with the expected
     *       sequence.</li>
     * </ol>
     */
    public Result append(long producerId, int baseSequence, List<String> records) {
        ProducerState state = producers.computeIfAbsent(producerId, id -> new ProducerState());
        int lastSeq = baseSequence + records.size() - 1;

        // 1. a retry of a batch we already wrote: say where it went, write nothing
        for (BatchInfo b : state.recent) {
            if (b.firstSeq() == baseSequence && b.lastSeq() == lastSeq) {
                return new Duplicate(b.baseOffset());
            }
        }

        // 3. not the next batch: refuse, so the producer resends in order
        if (baseSequence != state.nextSeq) {
            return new OutOfOrder(state.nextSeq);
        }

        // 2. the next batch: append it and remember it
        long baseOffset = log.size();
        log.addAll(records);
        state.recent.addLast(new BatchInfo(baseSequence, lastSeq, baseOffset));
        if (state.recent.size() > BATCHES_TO_RETAIN) state.recent.removeFirst();
        state.nextSeq = lastSeq + 1;
        return new Appended(baseOffset);
    }
}
