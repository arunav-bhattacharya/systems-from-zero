package sfz.msg.l12;

import redis.clients.jedis.RedisClient;
import redis.clients.jedis.StreamEntryID;
import redis.clients.jedis.exceptions.JedisDataException;
import redis.clients.jedis.resps.StreamEntry;

import java.time.Duration;

/**
 * One member of a consumer group that settles payments from a stream. Several workers with different consumer names
 * share the group, and Redis gives each new entry to exactly one of them.
 *
 * <p>An entry is done only when the worker acknowledges it with XACK. Until then it sits in the group's pending
 * entries list (PEL) under this worker's name, and if this worker dies, another one can claim it.
 */
public final class SettlementWorker {

    /** Settles one entry. Returning means done; throwing means not done, and the entry must stay pending. */
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

    /**
     * Done for you. {@code XGROUP CREATE <stream> <group> $ MKSTREAM}: the group starts at the end of the stream, so it
     * sees only entries added from now on, and the stream is created if it doesn't exist. Every worker can call this on
     * start: it returns false when the group already exists (Redis answers BUSYGROUP).
     */
    public boolean createGroup() {
        try {
            redis.xgroupCreate(stream, group, StreamEntryID.XGROUP_LAST_ENTRY, true);
            return true;
        } catch (JedisDataException e) {
            if (e.getMessage() != null && e.getMessage().startsWith("BUSYGROUP")) return false;
            throw e;
        }
    }

    /**
     * Reads up to {@code count} entries that no consumer in the group has seen yet, settles each one, and returns how
     * many it acknowledged. Don't wait for new entries: this call returns at once (a real loop adds {@code BLOCK}).
     *
     * <ol>
     *   <li>{@code XREADGROUP GROUP <group> <consumer> COUNT <count> STREAMS <stream> >}: in Jedis,
     *       {@code redis.xreadGroup(group, consumer, XReadGroupParams.xReadGroupParams().count(count),
     *       Map.of(stream, StreamEntryID.XREADGROUP_UNDELIVERED_ENTRY))}. It returns null or an empty list when there
     *       is nothing new, else one {@code Map.Entry<stream, List<StreamEntry>>} per stream.</li>
     *   <li>For each entry call {@code handler.handle(entry)}. If it returns, {@code redis.xack(stream, group,
     *       entry.getID())}. If it throws, catch the exception and leave the entry pending.</li>
     * </ol>
     */
    public int processNew(int count) {
        throw new UnsupportedOperationException("TODO: XREADGROUP >, handle, XACK");
    }

    /**
     * Takes over entries that any consumer of the group read but has not acknowledged for at least {@code minIdle},
     * settles them and acknowledges them, and returns how many it acknowledged.
     *
     * <p>{@code XAUTOCLAIM <stream> <group> <consumer> <minIdle ms> <cursor> COUNT <count>}, in Jedis
     * {@code redis.xautoclaim(stream, group, consumer, minIdle.toMillis(), cursor,
     * XAutoClaimParams.xAutoClaimParams().count(count))}. Start with cursor {@code new StreamEntryID(0, 0)}. The reply's
     * key is the next cursor and its value the claimed entries, now owned by this consumer. Handle and acknowledge
     * them exactly as in {@link #processNew}, and call again with the new cursor until it comes back as 0-0.
     */
    public int recoverAbandoned(Duration minIdle, int count) {
        throw new UnsupportedOperationException("TODO: XAUTOCLAIM page by page, handle, XACK");
    }
}
