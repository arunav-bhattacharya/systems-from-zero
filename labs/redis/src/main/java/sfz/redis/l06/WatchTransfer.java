package sfz.redis.l06;

import redis.clients.jedis.RedisClient;

/**
 * Moves money between two balances, each a Redis string holding a whole number of cents, without ever
 * letting the source go below zero, using optimistic locking: WATCH, read, MULTI, EXEC, retry.
 *
 * <p>A missing balance counts as 0.
 */
public final class WatchTransfer {
    public enum Outcome { DONE, INSUFFICIENT_FUNDS }

    /** What happened, and how many attempts it took (1 when nobody got in the way). */
    public record Result(Outcome outcome, int attempts) {}

    /** Give up (throw IllegalStateException) after this many aborted attempts. */
    public static final int MAX_ATTEMPTS = 1_000;

    private final RedisClient redis;
    private final Runnable afterRead;

    public WatchTransfer(RedisClient redis) {
        this(redis, () -> {});
    }

    /**
     * {@code afterRead} runs once per attempt, right after you read the balance and before MULTI. The tests use it
     * to change the balance from another client at exactly the wrong moment. Call it; don't do anything else with it.
     */
    public WatchTransfer(RedisClient redis, Runnable afterRead) {
        this.redis = redis;
        this.afterRead = afterRead;
    }

    /**
     * Moves {@code amount} from {@code from} to {@code to}. Each attempt:
     *
     * <ol>
     *   <li>{@code try (AbstractTransaction tx = redis.transaction(false))}: a transaction object that holds one
     *       connection and has not sent MULTI yet.</li>
     *   <li>{@code tx.watch(from)}, then read the balance with {@code tx.get(from).get()} and call {@code afterRead.run()}.
     *       Before {@code multi()}, a Jedis transaction runs each command at once on its own connection.</li>
     *   <li>Not enough money: {@code tx.unwatch()} and return INSUFFICIENT_FUNDS.</li>
     *   <li>Otherwise {@code tx.multi()}, queue {@code tx.decrBy(from, amount)} and {@code tx.incrBy(to, amount)},
     *       and {@code tx.exec()}. A non-null result means it ran: return DONE. Null means {@code from} changed
     *       after WATCH and nothing ran: go round again.</li>
     * </ol>
     */
    public Result transfer(String from, String to, long amount) {
        throw new UnsupportedOperationException("TODO: WATCH, GET, MULTI, DECRBY, INCRBY, EXEC, retry on null");
    }
}
