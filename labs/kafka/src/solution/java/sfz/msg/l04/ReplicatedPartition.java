package sfz.msg.l04;

import org.apache.kafka.common.errors.NotEnoughReplicasException;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

public final class ReplicatedPartition {

    public enum Acks { ONE, ALL }

    private final int leader;
    private final int minInsyncReplicas;
    private final long replicaLagTimeMaxMs;
    private final Map<Integer, Long> logEndOffset = new TreeMap<>();
    private final Map<Integer, Long> lastCaughtUpMs = new TreeMap<>();
    private final Set<Integer> isr = new TreeSet<>();
    private long highWatermark = 0;

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

    public Set<Integer> isr() { return Collections.unmodifiableSet(new TreeSet<>(isr)); }

    public long highWatermark() { return highWatermark; }

    public long logEndOffset(int replica) { return logEndOffset.get(replica); }

    public boolean isCommitted(long offset) { return offset < highWatermark; }

    public long append(int records, Acks acks) {
        // min.insync.replicas is checked before the write, and only for acks=all
        if (acks == Acks.ALL && isr.size() < minInsyncReplicas) {
            throw new NotEnoughReplicasException(
                    "ISR " + isr + " has " + isr.size() + " members, min.insync.replicas is " + minInsyncReplicas);
        }
        long leo = logEndOffset.get(leader) + records;
        logEndOffset.put(leader, leo);
        advanceHighWatermark(); // with the leader alone in the ISR, the write is committed at once
        return leo - 1;
    }

    public void fetch(int replica, long fetchOffset, long nowMs) {
        long leaderLeo = logEndOffset.get(leader);
        if (fetchOffset > leaderLeo) throw new IllegalArgumentException("fetch past the leader's log end offset");
        logEndOffset.put(replica, fetchOffset);              // it has everything below fetchOffset
        if (fetchOffset == leaderLeo) lastCaughtUpMs.put(replica, nowMs);
        if (!isr.contains(replica) && fetchOffset >= highWatermark) isr.add(replica); // caught up to the HW: back in
        advanceHighWatermark();
    }

    public void shrinkIsr(long nowMs) {
        long leaderLeo = logEndOffset.get(leader);
        // fetching is not enough: a follower must have reached the end within replica.lag.time.max.ms
        isr.removeIf(r -> r != leader
                && logEndOffset.get(r) < leaderLeo
                && nowMs - lastCaughtUpMs.get(r) > replicaLagTimeMaxMs);
        advanceHighWatermark();
    }

    private void advanceHighWatermark() {
        long minLeo = isr.stream().mapToLong(logEndOffset::get).min().orElseThrow();
        highWatermark = Math.max(highWatermark, minLeo); // the HW only ever moves forward
    }
}
