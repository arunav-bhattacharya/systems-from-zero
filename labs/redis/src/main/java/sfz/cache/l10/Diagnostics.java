package sfz.cache.l10;

import redis.clients.jedis.RedisClient;

import java.util.List;

/**
 * The two questions to ask first when every client of a Redis gets slow at once: which commands held the
 * one command thread, and which keys are so big that touching them is slow.
 */
public final class Diagnostics {
    /** One slow log entry: its id, how long the command ran on the server (microseconds), and its arguments. */
    public record SlowCommand(long id, long micros, List<String> args) {}

    /** One key, its type (string, hash, list, set, zset, stream) and the bytes {@code MEMORY USAGE} reports for it. */
    public record BigKey(String key, String type, long bytes) {}

    private final RedisClient redis;

    public Diagnostics(RedisClient redis) {
        this.redis = redis;
    }

    /**
     * The {@code n} slowest commands in the slow log, slowest first.
     *
     * <p>Read the whole log with {@code SLOWLOG GET 128}. Jedis's {@code RedisClient} has no method for it, so send
     * the command yourself and let Jedis parse the reply:
     * {@code Slowlog.from((List<Object>) redis.executeCommand(new CommandArguments(Protocol.Command.SLOWLOG).add("GET").add(128)))}. Each
     * {@code Slowlog} has {@code getId()}, {@code getExecutionTime()} (microseconds) and {@code getArgs()}.
     *
     * <p>The server returns the newest entry first. That is the wrong order for this question: sort by time spent.
     */
    public List<SlowCommand> slowest(int n) {
        throw new UnsupportedOperationException("TODO: SLOWLOG GET, sorted by execution time");
    }

    /**
     * The {@code n} biggest keys whose names match {@code pattern} (a glob such as {@code "payments:*"}), biggest first.
     *
     * <p>Walk the keyspace with SCAN, never KEYS: {@code redis.scan(cursor, new ScanParams().match(pattern).count(500))},
     * starting from {@code ScanParams.SCAN_POINTER_START} ("0") and stopping when the returned cursor is "0" again.
     * Each call does a small slice of the work, so other clients are served in between. SCAN may return a key twice;
     * count each key once. For every key, ask {@code redis.memoryUsage(key)} and {@code redis.type(key)}.
     */
    public List<BigKey> biggestKeys(String pattern, int n) {
        throw new UnsupportedOperationException("TODO: SCAN with MATCH, MEMORY USAGE per key, keep the n biggest");
    }
}
