package sfz.redis.l09;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.StreamEntryID;
import redis.clients.jedis.exceptions.JedisDataException;
import redis.clients.jedis.params.XAutoClaimParams;
import redis.clients.jedis.params.XReadGroupParams;
import redis.clients.jedis.resps.StreamEntry;

import java.time.Duration;
import java.util.List;
import java.util.Map;

public final class SettlementWorker {

    @FunctionalInterface
    public interface Handler {
        void handle(StreamEntry entry) throws Exception;
    }

    private final RedisClient redis;
    private final String stream;
    private final String group;
    private final String consumer;
    private final Handler handler;

    public SettlementWorker(RedisClient redis, String stream, String group, String consumer, Handler handler) {
        this.redis = redis;
        this.stream = stream;
        this.group = group;
        this.consumer = consumer;
        this.handler = handler;
    }

    public boolean createGroup() {
        try {
            redis.xgroupCreate(stream, group, StreamEntryID.XGROUP_LAST_ENTRY, true);
            return true;
        } catch (JedisDataException e) {
            if (e.getMessage() != null && e.getMessage().startsWith("BUSYGROUP")) return false;
            throw e;
        }
    }

    public int processNew(int count) {
        // '>' means: entries never delivered to anyone in this group. Each one joins the PEL under our name.
        List<Map.Entry<String, List<StreamEntry>>> reply = redis.xreadGroup(group, consumer,
                XReadGroupParams.xReadGroupParams().count(count),
                Map.of(stream, StreamEntryID.XREADGROUP_UNDELIVERED_ENTRY));
        if (reply == null) return 0;
        int acked = 0;
        for (Map.Entry<String, List<StreamEntry>> perStream : reply) {
            for (StreamEntry entry : perStream.getValue()) {
                if (settle(entry)) acked++;
            }
        }
        return acked;
    }

    public int recoverAbandoned(Duration minIdle, int count) {
        StreamEntryID start = new StreamEntryID(0, 0);
        StreamEntryID cursor = start;
        int acked = 0;
        do {
            // only entries idle for at least minIdle: a worker that is slow but alive keeps its entries
            Map.Entry<StreamEntryID, List<StreamEntry>> page = redis.xautoclaim(stream, group, consumer,
                    minIdle.toMillis(), cursor, XAutoClaimParams.xAutoClaimParams().count(count));
            for (StreamEntry entry : page.getValue()) {
                if (settle(entry)) acked++;
            }
            cursor = page.getKey();                               // 0-0 once the whole PEL has been scanned
        } while (cursor.compareTo(start) != 0);
        return acked;
    }

    private boolean settle(StreamEntry entry) {
        try {
            handler.handle(entry);
        } catch (Exception e) {
            return false;                                         // not done: it stays pending, to be retried or claimed
        }
        redis.xack(stream, group, entry.getID());                 // done: out of the PEL. A crash before this line means
        return true;                                              // the entry is handled again: at-least-once
    }
}
