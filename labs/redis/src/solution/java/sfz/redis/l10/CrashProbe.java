package sfz.redis.l10;

import redis.clients.jedis.CommandArguments;
import redis.clients.jedis.Protocol;
import redis.clients.jedis.RedisClient;

import java.util.stream.IntStream;

public final class CrashProbe {
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

    public void write(String prefix, int from, int to) {
        for (int i = from; i < to; i++) {
            redis.set(prefix + i, "settled");             // returns only after the server said OK
        }
    }

    public int count(String prefix, int from, int to) {
        if (to <= from) return 0;
        String[] keys = IntStream.range(from, to).mapToObj(i -> prefix + i).toArray(String[]::new);
        return (int) redis.exists(keys);                   // EXISTS k1 k2 ... counts the ones present
    }

    public long persistenceStat(String field) {
        return Long.parseLong(infoField(field));
    }

    public void snapshot() {
        redis.executeCommand(new CommandArguments(Protocol.Command.BGSAVE));   // forks; the reply comes before the file is written
        while (persistenceStat("rdb_bgsave_in_progress") != 0) {
            sleep(5);                                      // the child is still writing temp-<pid>.rdb
        }
        // the child renames its temp file over dump.rdb only when the whole file is written
        if (!"ok".equals(infoField("rdb_last_bgsave_status"))) {
            throw new IllegalStateException("BGSAVE failed: " + infoField("rdb_last_bgsave_status"));
        }
    }

    public Loss writeThenCrash(String prefix, int n) {
        write(prefix, 0, n);
        crash.run();                                       // kill -9: no shutdown, no final save
        return new Loss(n, count(prefix, 0, n));
    }

    private String infoField(String field) {
        for (String line : redis.info("persistence").split("\r?\n")) {
            if (line.startsWith(field + ":")) return line.substring(field.length() + 1).trim();
        }
        throw new IllegalArgumentException("no such field in INFO persistence: " + field);
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
    }
}
