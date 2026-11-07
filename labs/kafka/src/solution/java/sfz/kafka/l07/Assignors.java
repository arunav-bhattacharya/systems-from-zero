package sfz.kafka.l07;

import org.apache.kafka.common.TopicPartition;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

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
        List<String> sorted = members.stream().sorted().toList();
        Map<String, List<TopicPartition>> result = emptyResult(sorted);
        for (var topic : new TreeMap<>(partitionsPerTopic).entrySet()) {
            int partitions = topic.getValue();
            int perMember = partitions / sorted.size();      // everyone gets at least this many
            int withExtra = partitions % sorted.size();      // the first few members get one more
            for (int i = 0; i < sorted.size(); i++) {
                int start = i * perMember + Math.min(i, withExtra);
                int length = perMember + (i < withExtra ? 1 : 0);
                for (int p = start; p < start + length; p++) {
                    result.get(sorted.get(i)).add(new TopicPartition(topic.getKey(), p));
                }
            }
        }
        return result;
    }

    /**
     * Kafka's {@code RoundRobinAssignor}: list every partition of every topic (sorted by topic, then partition)
     * and deal them out one at a time to the members, sorted by id, like cards.
     */
    public static Map<String, List<TopicPartition>> roundRobin(List<String> members, Map<String, Integer> partitionsPerTopic) {
        List<String> sorted = members.stream().sorted().toList();
        Map<String, List<TopicPartition>> result = emptyResult(sorted);
        int next = 0;
        for (var topic : new TreeMap<>(partitionsPerTopic).entrySet()) {
            for (int p = 0; p < topic.getValue(); p++) {
                result.get(sorted.get(next)).add(new TopicPartition(topic.getKey(), p));
                next = (next + 1) % sorted.size();           // the next card goes to the next member
            }
        }
        return result;
    }

    private static Map<String, List<TopicPartition>> emptyResult(List<String> sortedMembers) {
        Map<String, List<TopicPartition>> result = new TreeMap<>();
        for (String m : sortedMembers) result.put(m, new ArrayList<>());
        return result;
    }
}
