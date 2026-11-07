package sfz.kafka.l09;

import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.clients.producer.Producer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.errors.ProducerFencedException;

import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

/**
 * Consume, transform, produce, with a Kafka transaction around each batch: every payment becomes ledger entries in
 * {@code outputTopic}, and the entries and the consumer's new committed offsets become visible together, or not at
 * all.
 *
 * <p>The producer has a {@code transactional.id}. The consumer has {@code enable.auto.commit=false} and never
 * commits by itself: its offsets travel inside the transaction.
 */
public final class LedgerTransformer {
    private final Consumer<String, String> consumer;
    private final Producer<String, String> producer;
    private final String outputTopic;
    private final Function<ConsumerRecord<String, String>, List<String>> entriesFor;

    /**
     * @param entriesFor the transformation: the ledger entry values for one payment, written in this order with the
     *                   payment's key. It may throw, which stands for a crash in the middle of a batch.
     */
    public LedgerTransformer(Consumer<String, String> consumer, Producer<String, String> producer, String outputTopic,
                             Function<ConsumerRecord<String, String>, List<String>> entriesFor) {
        this.consumer = consumer;
        this.producer = producer;
        this.outputTopic = outputTopic;
        this.entriesFor = entriesFor;
    }

    /**
     * Registers the producer's {@code transactional.id} with the transaction coordinator: {@code initTransactions()}.
     * Call it once, before the first batch. It aborts whatever an older producer with the same id left open, and it
     * fences that producer.
     */
    public void init() {
        throw new UnsupportedOperationException("TODO: producer.initTransactions()");
    }

    /**
     * One batch, in one transaction.
     *
     * <ol>
     *   <li>{@code poll(timeout)}; return 0 if it returned nothing.</li>
     *   <li>{@code beginTransaction()}, then for each record, in order, send one record to {@code outputTopic} per
     *       entry from {@code entriesFor}, with the payment's key.</li>
     *   <li>{@code sendOffsetsToTransaction} with the next offset to read of every partition in the batch and
     *       {@code consumer.groupMetadata()}, then {@code commitTransaction()}. Return the number of payments.</li>
     * </ol>
     *
     * <p>If anything in steps 2 and 3 throws:
     * <ul>
     *   <li>a {@link ProducerFencedException}: let it out untouched. A newer producer owns the transactional.id, and
     *       this one must be closed.</li>
     *   <li>anything else: {@code abortTransaction()}, then rewind the consumer: seek every partition of the batch
     *       back to its first record in the batch, so the next call reads the batch again. Then rethrow. (If the
     *       abort itself throws, let that exception out instead.)</li>
     * </ul>
     */
    public int processOnce(Duration timeout) {
        throw new UnsupportedOperationException("TODO: poll; begin; send the entries; sendOffsetsToTransaction; commit. On failure: abort, rewind, rethrow");
    }
}
