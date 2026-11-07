package sfz.redis.l07;

import redis.clients.jedis.RedisClient;

/**
 * A sliding-window log rate limiter: at most {@code limit} admitted requests per subject (a card, a merchant's
 * API key) in any span of {@code windowMillis}.
 *
 * <p>Each subject has one sorted set, {@code prefix + subject}. Every admitted request is one member, scored by the
 * time it was admitted in milliseconds. A refused request is not recorded.
 *
 * <p>The caller passes the time in, so the tests can control the clock. A request at time {@code t} counts against
 * the window while {@code now - t < windowMillis}.
 */
public final class SlidingWindowLimiter {

    /**
     * The whole decision as one script. KEYS[1] is the subject's sorted set. ARGV[1] is now (ms), ARGV[2] the window
     * (ms), ARGV[3] the limit and ARGV[4] a member name that is unique to this request. Write it so that it:
     *
     * <ol>
     *   <li>removes the entries that left the window, every score up to and including {@code now - window}:
     *       {@code redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)}, with {@code now} and
     *       {@code window} turned into numbers by {@code tonumber(ARGV[...])},</li>
     *   <li>counts what is left with {@code ZCARD},</li>
     *   <li>if the count is already at the limit, returns 0 and writes nothing,</li>
     *   <li>otherwise adds the request with {@code ZADD KEYS[1] now member}, sets {@code PEXPIRE KEYS[1] window} so an
     *       idle subject's key disappears, and returns 1.</li>
     * </ol>
     */
    public static final String SCRIPT = "return redis.error_reply('TODO: write the sliding-window script')";

    private final RedisClient redis;
    private final String prefix;
    private final int limit;
    private final long windowMillis;

    public SlidingWindowLimiter(RedisClient redis, String prefix, int limit, long windowMillis) {
        this.redis = redis;
        this.prefix = prefix;
        this.limit = limit;
        this.windowMillis = windowMillis;
    }

    /** The sorted set that holds {@code subject}'s window. Done for you. */
    public String key(String subject) {
        return prefix + subject;
    }

    /**
     * Returns true if the request is admitted (and recorded), false if {@code subject} already has {@code limit}
     * requests in the window that ends at {@code nowMillis}.
     *
     * <p>Run {@link #SCRIPT} with {@code redis.eval(SCRIPT, List.of(key(subject)), List.of(...))}: the four arguments
     * as strings, with {@code UUID.randomUUID().toString()} as the member. The script's 0 or 1 arrives as a
     * {@code Long}.
     */
    public boolean tryAcquire(String subject, long nowMillis) {
        throw new UnsupportedOperationException("TODO: run the sliding-window script with EVAL");
    }
}
