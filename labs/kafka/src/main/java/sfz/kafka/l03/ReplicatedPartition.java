package sfz.kafka.l03;

import org.apache.kafka.common.errors.NotEnoughReplicasException;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * One partition with a leader and followers, seen from the leader. It models the bookkeeping a Kafka leader
 * does: each replica's log end offset (LEO), the in-sync replica set (ISR) and the high watermark (HW).
 * No data moves here, only offsets. Time is passed in as {@code nowMs}, so tests control the clock.
 */
public final class ReplicatedPartition {

    /** The producer's {@code acks} setting. */
    public enum Acks {
        /** {@code acks=1}: the leader has written it. */
        ONE,
        /** {@code acks=all}: every replica in the ISR has it. */
        ALL
    }

    private final int leader;
    private final int minInsyncReplicas;
    private final long replicaLagTimeMaxMs;
    private final Map<Integer, Long> logEndOffset = new TreeMap<>();   // every replica, the leader included
    private final Map<Integer, Long> lastCaughtUpMs = new TreeMap<>(); // followers only
    private final Set<Integer> isr = new TreeSet<>();
    private long highWatermark = 0;

    /**
     * A new, empty partition. Every replica starts in the ISR with LEO 0, caught up at {@code nowMs}.
     *
     * @param replicas            broker ids, the leader included
     * @param minInsyncReplicas   the topic's {@code min.insync.replicas} (Kafka's default is 1)
     * @param replicaLagTimeMaxMs the broker's {@code replica.lag.time.max.ms} (Kafka's default is 30000)
     */
    public ReplicatedPartition(int leader, List<Integer> replicas, int minInsyncReplicas, long replicaLagTimeMaxMs, long nowMs) {
        if (!replicas.contains(leader)) throw new IllegalArgumentException("the leader must be one of the replicas");
        this.leader = leader;
        this.minInsyncReplicas = minInsyncReplicas;
        this.replicaLagTimeMaxMs = replicaLagTimeMaxMs;
        for (int r : replicas) {
            logEndOffset.put(r, 0L);
            isr.add(r);
            if (r != leader) lastCaughtUpMs.put(r, nowMs);
        }
    }

    public int leader() { return leader; }

    /** The current ISR, as a read-only copy in id order. */
    public Set<Integer> isr() { return Collections.unmodifiableSet(new TreeSet<>(isr)); }

    public long highWatermark() { return highWatermark; }

    public long logEndOffset(int replica) { return logEndOffset.get(replica); }

    /** Committed means below the high watermark: every ISR member has it. Consumers only ever see committed records. */
    public boolean isCommitted(long offset) { return offset < highWatermark; }

    /**
     * A producer writes {@code records} new records to the leader. Returns the offset of the last one.
     *
     * <ul>
     *   <li>With {@link Acks#ALL}, first check the ISR: if it has fewer than {@code minInsyncReplicas} members,
     *       write nothing and throw {@link NotEnoughReplicasException}. This is the only place
     *       {@code min.insync.replicas} matters.</li>
     *   <li>With {@link Acks#ONE} the check does not apply.</li>
     *   <li>Then move the leader's LEO forward by {@code records}, and let the HW advance (the ISR may be
     *       just the leader).</li>
     * </ul>
     */
    public long append(int records, Acks acks) {
        throw new UnsupportedOperationException("TODO: check min.insync.replicas for acks=all, bump the leader's LEO, advance the HW");
    }

    /**
     * Follower {@code replica} sends a fetch request for offset {@code fetchOffset}: it already has every
     * record below that offset. A {@code fetchOffset} past the leader's LEO throws {@link IllegalArgumentException}.
     *
     * <ol>
     *   <li>The follower's LEO becomes {@code fetchOffset}.</li>
     *   <li>If {@code fetchOffset} equals the leader's LEO, the follower is caught up: set its last caught-up time to
     *       {@code nowMs}. (Real Kafka also counts a follower as caught up if it reached the leader's LEO as of its
     *       previous fetch. The model leaves that out.)</li>
     *   <li>A follower outside the ISR rejoins it once its LEO is at least the high watermark.</li>
     *   <li>Let the HW advance.</li>
     * </ol>
     */
    public void fetch(int replica, long fetchOffset, long nowMs) {
        throw new UnsupportedOperationException("TODO: record the follower's LEO, caught-up time and ISR membership, advance the HW");
    }

    /**
     * The leader's periodic ISR check. Remove every follower that is behind the leader's LEO and whose last
     * caught-up time is more than {@code replicaLagTimeMaxMs} before {@code nowMs}. A follower that already has
     * everything stays, even if it has not fetched for a while: an idle partition gives it nothing to fetch.
     * (A broker that has died leaves the ISR another way: the controller fences it.) The leader never leaves.
     * Then let the HW advance: a slow follower that held it back no longer counts.
     */
    public void shrinkIsr(long nowMs) {
        throw new UnsupportedOperationException("TODO: drop followers that have not caught up within replicaLagTimeMaxMs, advance the HW");
    }

    /** HW = the smallest LEO among the ISR members. It never moves backwards. */
    private void advanceHighWatermark() {
        throw new UnsupportedOperationException("TODO: min LEO over the ISR, and never lower than it already is");
    }
}
