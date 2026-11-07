package sfz.kafka.l07;

import org.apache.kafka.common.TopicPartition;

import java.util.List;
import java.util.Map;

/**
 * Two of the classic protocol's client-side assignors, written out so you can see what they compute.
 * Every member subscribes to every topic in {@code partitionsPerTopic}.
 *
 * <p>Both return a map with one entry per member (an empty list for a member that gets nothing), and each list
 * sorted by topic name, then partition number.
 */
public final class Assignors {
    private Assignors() {
    }

    /**
     * Kafka's {@code RangeAssignor}. Topic by topic, with the members sorted by id: divide the topic's partitions
     * into contiguous ranges, one per member. With 7 partitions and 3 members the ranges have 3, 2 and 2
     * partitions; the first {@code partitions % members} members get the extra one.
     */
    public static Map<String, List<TopicPartition>> range(List<String> members, Map<String, Integer> partitionsPerTopic) {
        throw new UnsupportedOperationException("TODO: per topic, sorted members, contiguous ranges; the first partitions % members get one extra");
    }

    /**
     * Kafka's {@code RoundRobinAssignor}: list every partition of every topic (sorted by topic, then partition)
     * and deal them out one at a time to the members, sorted by id, like cards.
     */
    public static Map<String, List<TopicPartition>> roundRobin(List<String> members, Map<String, Integer> partitionsPerTopic) {
        throw new UnsupportedOperationException("TODO: deal all partitions, sorted by topic then partition, to the sorted members in turn");
    }
}
