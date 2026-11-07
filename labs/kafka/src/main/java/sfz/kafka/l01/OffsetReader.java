package sfz.kafka.l01;

import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.TopicPartition;

import java.time.Duration;
import java.util.List;

/** Reads a slice of one real Kafka partition: the broker version of {@code MiniLog.read}. */
public final class OffsetReader {
    private OffsetReader() {}

    /**
     * Returns up to {@code max} records of partition {@code tp}, starting at offset {@code from}, in offset order.
     *
     * <ol>
     *   <li>Take the partition with {@code consumer.assign(...)}. Do not {@code subscribe}: there is no
     *       consumer group here, so nothing else can be given this partition.</li>
     *   <li>Set the consumer's position with {@code consumer.seek(tp, from)}.</li>
     *   <li>Call {@code consumer.poll(Duration.ofMillis(200))} in a loop and collect the records of {@code tp}
     *       until you have {@code max} of them or {@code timeout} has passed. One poll may return fewer records
     *       than you want, none at all, or more than you need: keep only the first {@code max}.</li>
     * </ol>
     *
     * Commit nothing. The consumer belongs to no group, so there is nowhere to commit to.
     */
    public static List<ConsumerRecord<String, String>> readFrom(
            Consumer<String, String> consumer, TopicPartition tp, long from, int max, Duration timeout) {
        throw new UnsupportedOperationException("TODO: assign, seek, then poll until you have max records");
    }
}
