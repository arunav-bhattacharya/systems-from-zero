package sfz.redis.l01;

import redis.clients.jedis.RedisClient;

import java.util.concurrent.CompletableFuture;

public final class SlowScriptProbe {

    public static final String BUSY_SCRIPT = """
            local stop = os.clock() + tonumber(ARGV[1]) / 1000
            while os.clock() < stop do end
            return 1
            """;

    public static final long HEAD_START_MS = 200;

    public record Timing(String value, long millis) {}

    private SlowScriptProbe() {}

    public static Timing timeGet(RedisClient app, String key) {
        long t0 = System.nanoTime();
        String value = app.get(key);
        return new Timing(value, (System.nanoTime() - t0) / 1_000_000);
    }

    public static Timing timeGetDuringScript(RedisClient scripts, RedisClient app, String key, long scriptMillis) {
        // 1. eval blocks its caller until the script returns, so it gets a thread of its own
        CompletableFuture<Object> script = CompletableFuture.supplyAsync(
                () -> scripts.eval(BUSY_SCRIPT, 0, String.valueOf(scriptMillis)));
        // 2. give the server time to read the EVAL and start spinning
        try {
            Thread.sleep(HEAD_START_MS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
        // 3. a different connection, a different key: the GET still waits, because one thread runs every command
        Timing timing = timeGet(app, key);
        // 4. join() rethrows anything the script threw (wrapped in CompletionException)
        script.join();
        return timing;
    }
}
