package sfz.redis.l09.demo;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.StreamEntryID;
import redis.clients.jedis.params.XAddParams;
import redis.clients.jedis.params.XAutoClaimParams;
import redis.clients.jedis.params.XPendingParams;
import redis.clients.jedis.params.XReadGroupParams;
import redis.clients.jedis.resps.StreamEntry;
import redis.clients.jedis.resps.StreamPendingEntry;

import java.util.List;
import java.util.Map;

/** Worker w1 reads three payments and dies before XACK. Worker w3 claims them once they have been idle for 1 s. */
public class CrashRecoveryDemo {
    static final String STREAM = "demo:l09:payments";
    static final String GROUP = "settlers";

    static List<StreamEntry> readNew(RedisClient redis, String consumer, int count) {
        List<Map.Entry<String, List<StreamEntry>>> reply = redis.xreadGroup(GROUP, consumer,
                XReadGroupParams.xReadGroupParams().count(count), Map.of(STREAM, StreamEntryID.XREADGROUP_UNDELIVERED_ENTRY));
        return reply == null || reply.isEmpty() ? List.of() : reply.get(0).getValue();
    }

    static void printPending(RedisClient redis) {
        List<StreamPendingEntry> pending = redis.xpending(STREAM, GROUP, XPendingParams.xPendingParams("-", "+", 10));
        System.out.println("  XPENDING: " + pending.size() + " pending");
        for (StreamPendingEntry p : pending) {
            System.out.printf("    %s owner=%s idle=%d ms deliveries=%d%n",
                    redis.xrange(STREAM, p.getID(), p.getID()).get(0).getFields().get("payment"),
                    p.getConsumerName(), p.getIdleTime(), p.getDeliveredTimes());
        }
    }

    public static void main(String[] args) throws Exception {
        try (RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6379).build()) {
            redis.del(STREAM);
            redis.xgroupCreate(STREAM, GROUP, StreamEntryID.XGROUP_LAST_ENTRY, true);   // XGROUP CREATE ... $ MKSTREAM
            for (int i = 1; i <= 5; i++) {
                redis.xadd(STREAM, XAddParams.xAddParams(), Map.of("payment", "p-" + i, "amount", String.valueOf(1000 + i)));
            }

            List<StreamEntry> w1 = readNew(redis, "w1", 3);          // w1 takes three... and its pod is killed
            List<StreamEntry> w2 = readNew(redis, "w2", 10);         // w2 takes the rest and settles them
            for (StreamEntry e : w2) redis.xack(STREAM, GROUP, e.getID());
            System.out.println("w1 read " + w1.size() + " and crashed; w2 read " + w2.size() + " and acknowledged them");
            printPending(redis);

            var early = redis.xautoclaim(STREAM, GROUP, "w3", 1_000, new StreamEntryID(0, 0),
                    XAutoClaimParams.xAutoClaimParams().count(100));
            System.out.println("w3 XAUTOCLAIM min-idle 1000 ms, right away: claimed " + early.getValue().size());

            Thread.sleep(1_100);
            var claimed = redis.xautoclaim(STREAM, GROUP, "w3", 1_000, new StreamEntryID(0, 0),
                    XAutoClaimParams.xAutoClaimParams().count(100));
            System.out.println("w3 XAUTOCLAIM min-idle 1000 ms, 1.1 s later: claimed " + claimed.getValue().size()
                    + ", next cursor " + claimed.getKey());
            printPending(redis);
            for (StreamEntry e : claimed.getValue()) redis.xack(STREAM, GROUP, e.getID());   // settle, then ack
            System.out.println("w3 acknowledged them. XPENDING total: " + redis.xpending(STREAM, GROUP).getTotal());
        }
    }
}
