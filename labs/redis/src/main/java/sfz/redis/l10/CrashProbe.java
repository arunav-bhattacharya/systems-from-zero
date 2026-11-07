package sfz.redis.l10;

import redis.clients.jedis.RedisClient;

/**
 * Measures what a crash costs: write some payments, kill the server with {@code kill -9}, let it restart,
 * and count what came back from disk.
 *
 * <p>Every write here is acknowledged: {@code SET} returns {@code OK} before the next one is sent. So any
 * key missing after the restart is a payment the server said it had, and then forgot.
 *
 * <p>The tests run this against a server with different persistence settings (none, an RDB snapshot,
 * the append-only file with each fsync policy). {@code crash} is supplied by them: it kills the server
 * process and returns once a new process has loaded its files and answers PING.
 */
public final class CrashProbe {
    /** What one experiment wrote, and how much of it survived the crash. */
    public record Loss(int written, int survived) {
        public int lost() {
            return written - survived;
        }
    }

    private final RedisClient redis;
    private final Runnable crash;

    public CrashProbe(RedisClient redis, Runnable crash) {
        this.redis = redis;
        this.crash = crash;
    }

    /**
     * Writes the payments {@code prefix + i} for every {@code i} from {@code from} (inclusive) to {@code to}
     * (exclusive), each with the value {@code "settled"}, one {@code SET} at a time.
     */
    public void write(String prefix, int from, int to) {
        throw new UnsupportedOperationException("TODO: one SET per payment, each acknowledged before the next");
    }

    /**
     * How many of the keys {@code prefix + i}, for {@code i} from {@code from} to {@code to} (exclusive),
     * exist now. {@code redis.exists(String...)} counts many keys in one round trip.
     */
    public int count(String prefix, int from, int to) {
        throw new UnsupportedOperationException("TODO: count the keys that exist");
    }

    /**
     * One number from {@code INFO persistence}, such as {@code rdb_bgsave_in_progress} or
     * {@code rdb_changes_since_last_save}. The reply is text: one {@code field:value} line per field.
     */
    public long persistenceStat(String field) {
        throw new UnsupportedOperationException("TODO: find the field's line in INFO persistence");
    }

    /**
     * Takes an RDB snapshot and returns only once it is safely on disk.
     *
     * <ol>
     *   <li>Send BGSAVE: {@code redis.executeCommand(new CommandArguments(Protocol.Command.BGSAVE))}. The server forks a child to write
     *       the file and answers at once, long before the file is complete.</li>
     *   <li>Poll {@code INFO persistence} every few milliseconds until {@code rdb_bgsave_in_progress} is 0. The
     *       server sets it to 1 before it answers BGSAVE, so the first poll can't miss the save.</li>
     *   <li>Throw {@link IllegalStateException} unless {@code rdb_last_bgsave_status} is {@code ok}. That field
     *       is text, so read it from the INFO reply yourself.</li>
     * </ol>
     */
    public void snapshot() {
        throw new UnsupportedOperationException("TODO: BGSAVE, then wait for the child to finish");
    }

    /**
     * The whole experiment: {@link #write} the payments 0 to {@code n} under {@code prefix}, run {@code crash},
     * then {@link #count} what survived.
     */
    public Loss writeThenCrash(String prefix, int n) {
        throw new UnsupportedOperationException("TODO: write, crash, count");
    }
}
