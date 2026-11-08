package sfz.txn.l06;

import redis.clients.jedis.AbstractTransaction;
import redis.clients.jedis.RedisClient;

public final class WatchTransfer {
    public enum Outcome { DONE, INSUFFICIENT_FUNDS }

    public record Result(Outcome outcome, int attempts) {}

    public static final int MAX_ATTEMPTS = 1_000;

    private final RedisClient redis;
    private final Runnable afterRead;

    public WatchTransfer(RedisClient redis) {
        this(redis, () -> {});
    }

    public WatchTransfer(RedisClient redis, Runnable afterRead) {
        this.redis = redis;
        this.afterRead = afterRead;
    }

    public Result transfer(String from, String to, long amount) {
        for (int attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            // transaction(false) pins one pooled connection and sends no MULTI yet; WATCH lives on that connection
            try (AbstractTransaction tx = redis.transaction(false)) {
                tx.watch(from);                                   // the decision reads only 'from', so watch only 'from'
                long balance = parse(tx.get(from).get());         // before multi() this runs at once, on the same connection
                afterRead.run();
                if (balance < amount) {
                    tx.unwatch();
                    return new Result(Outcome.INSUFFICIENT_FUNDS, attempt);
                }
                tx.multi();
                tx.decrBy(from, amount);                          // queued, not run yet
                tx.incrBy(to, amount);
                if (tx.exec() != null) return new Result(Outcome.DONE, attempt);
                // null: 'from' changed after WATCH, so Redis ran nothing; read again and retry
            }
        }
        throw new IllegalStateException("gave up after " + MAX_ATTEMPTS + " attempts");
    }

    private static long parse(String value) {
        return value == null ? 0 : Long.parseLong(value);
    }
}
