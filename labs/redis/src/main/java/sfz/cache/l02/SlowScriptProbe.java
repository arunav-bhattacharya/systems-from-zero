package sfz.cache.l02;

import redis.clients.jedis.RedisClient;

/**
 * Measures what one long-running Lua script does to every other client's latency.
 *
 * <p>Both methods time a plain {@code GET} with {@link System#nanoTime()}. The second one runs
 * a busy script on a different connection first, so you can see the GET wait for it.
 */
public final class SlowScriptProbe {

    /** Spins on the server's CPU for ARGV[1] milliseconds, then returns 1. Done for you. */
    public static final String BUSY_SCRIPT = """
            local stop = os.clock() + tonumber(ARGV[1]) / 1000
            while os.clock() < stop do end
            return 1
            """;

    /** How long to wait after starting the script before sending the GET, so the script is surely running. */
    public static final long HEAD_START_MS = 200;

    /** What a GET returned, and how many milliseconds the call took. */
    public record Timing(String value, long millis) {}

    private SlowScriptProbe() {}

    /** Times one {@code GET key} on {@code app}. */
    public static Timing timeGet(RedisClient app, String key) {
        throw new UnsupportedOperationException("TODO: time one GET with System.nanoTime()");
    }

    /**
     * Runs {@link #BUSY_SCRIPT} for {@code scriptMillis} on the {@code scripts} client, and while it runs,
     * times one {@code GET key} on the {@code app} client.
     *
     * <ol>
     *   <li>Start the script in a background thread: {@code scripts.eval(BUSY_SCRIPT, 0, "<millis>")}
     *       blocks its caller until the script returns.</li>
     *   <li>Sleep {@link #HEAD_START_MS} so the server is inside the script.</li>
     *   <li>Time the GET with {@link #timeGet}.</li>
     *   <li>Wait for the script to finish before you return, and let its exceptions escape.</li>
     * </ol>
     */
    public static Timing timeGetDuringScript(RedisClient scripts, RedisClient app, String key, long scriptMillis) {
        throw new UnsupportedOperationException("TODO: start the script, then time a GET on the other client");
    }
}
