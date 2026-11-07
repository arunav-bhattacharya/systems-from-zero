package sfz.redis.l11;

import redis.clients.jedis.CommandArguments;
import redis.clients.jedis.Protocol;
import redis.clients.jedis.RedisClient;
import redis.clients.jedis.params.ScanParams;
import redis.clients.jedis.resps.ScanResult;
import redis.clients.jedis.resps.Slowlog;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class Diagnostics {
    public record SlowCommand(long id, long micros, List<String> args) {}

    public record BigKey(String key, String type, long bytes) {}

    private final RedisClient redis;

    public Diagnostics(RedisClient redis) {
        this.redis = redis;
    }

    @SuppressWarnings("unchecked")
    public List<SlowCommand> slowest(int n) {
        List<Slowlog> log = Slowlog.from((List<Object>) redis.executeCommand(
                new CommandArguments(Protocol.Command.SLOWLOG).add("GET").add(128)));
        return log.stream()
                .sorted(Comparator.comparingLong(Slowlog::getExecutionTime).reversed())   // most time on the thread first
                .limit(n)
                .map(e -> new SlowCommand(e.getId(), e.getExecutionTime(), e.getArgs()))
                .toList();
    }

    public List<BigKey> biggestKeys(String pattern, int n) {
        ScanParams params = new ScanParams().match(pattern).count(500);
        Set<String> seen = new HashSet<>();                    // SCAN can return a key more than once
        List<BigKey> keys = new ArrayList<>();
        String cursor = ScanParams.SCAN_POINTER_START;
        do {
            ScanResult<String> page = redis.scan(cursor, params);   // a slice of the table, never the whole keyspace at once
            for (String key : page.getResult()) {
                if (!seen.add(key)) continue;
                Long bytes = redis.memoryUsage(key);
                if (bytes != null) keys.add(new BigKey(key, redis.type(key), bytes));   // null: deleted meanwhile
            }
            cursor = page.getCursor();
        } while (!cursor.equals(ScanParams.SCAN_POINTER_START));
        keys.sort(Comparator.comparingLong(BigKey::bytes).reversed());
        return List.copyOf(keys.subList(0, Math.min(n, keys.size())));
    }
}
