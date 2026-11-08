package sfz.msg.l02;

import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.TopicPartition;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

public final class OffsetReader {
    private OffsetReader() {}

    public static List<ConsumerRecord<String, String>> readFrom(
            Consumer<String, String> consumer, TopicPartition tp, long from, int max, Duration timeout) {
        consumer.assign(List.of(tp));   // take the partition directly: no group, no rebalance
        consumer.seek(tp, from);        // the consumer's position is one number per partition; set it

        List<ConsumerRecord<String, String>> out = new ArrayList<>(max);
        long deadline = System.nanoTime() + timeout.toNanos();
        while (out.size() < max && System.nanoTime() < deadline) {
            // a poll returns whatever the broker had ready: 0, a few, or up to max.poll.records (500)
            for (ConsumerRecord<String, String> r : consumer.poll(Duration.ofMillis(200)).records(tp)) {
                if (out.size() == max) break;
                out.add(r);
            }
        }
        return out;
    }
}
