package sfz.redis.l01.demo;

import io.lettuce.core.RedisFuture;
import io.lettuce.core.api.StatefulRedisConnection;
import io.lettuce.core.api.async.RedisAsyncCommands;
import redis.clients.jedis.RedisClient;

import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** The same GET through Jedis (blocking) and Lettuce (async), then how each one connected. */
public class ClientsDemo {
    public static void main(String[] args) throws Exception {
        // Jedis 8: one RedisClient, a pool of connections behind it, blocking calls
        try (RedisClient jedis = RedisClient.builder().hostAndPort("localhost", 6379).build()) {
            jedis.set("payment:42", "approved");
            System.out.println("Jedis   GET payment:42 -> " + jedis.get("payment:42"));

            // Lettuce 7: one connection shared by every caller, calls return futures
            io.lettuce.core.RedisClient lettuce = io.lettuce.core.RedisClient.create("redis://localhost:6379");
            try (StatefulRedisConnection<String, String> conn = lettuce.connect()) {
                RedisAsyncCommands<String, String> async = conn.async();
                RedisFuture<String> reply = async.get("payment:42");        // returns at once
                System.out.println("Lettuce GET payment:42 -> " + reply.get(1, TimeUnit.SECONDS));

                // ask the server how each library connected
                String list = async.clientList().get(1, TimeUnit.SECONDS);
                Pattern fields = Pattern.compile("(resp=\\d+) (lib-name=\\S+) (lib-ver=\\S+)");
                for (String line : list.split("\n")) {
                    Matcher m = fields.matcher(line);
                    if (m.find() && !m.group(2).equals("lib-name=")) {
                        System.out.println(m.group(1) + " " + m.group(2) + " " + m.group(3));
                    }
                }
            } finally {
                lettuce.shutdown();
            }
        }
    }
}
