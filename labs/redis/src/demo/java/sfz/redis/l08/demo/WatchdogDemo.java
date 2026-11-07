package sfz.redis.l08.demo;

import org.redisson.Redisson;
import org.redisson.api.RFencedLock;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.redisson.config.Config;
import redis.clients.jedis.RedisClient;

import java.util.concurrent.TimeUnit;

/** Watch Redisson's lock watchdog renew a lease, then a lock with a fixed lease run out, then fencing tokens. */
public class WatchdogDemo {
    static final String LOCK = "demo:l08:lock:settle";

    public static void main(String[] args) throws Exception {
        Config config = new Config();
        config.useSingleServer().setAddress("redis://localhost:6379");
        config.setLockWatchdogTimeout(3_000);                   // the default is 30 s; 3 s keeps the demo short
        RedissonClient redisson = Redisson.create(config);

        try (RedisClient redis = RedisClient.builder().hostAndPort("localhost", 6379).build()) {
            redis.del(LOCK);
            RLock lock = redisson.getLock(LOCK);

            lock.lock();                                         // no lease given: the watchdog keeps it alive
            System.out.println("lock() with the watchdog. Redis holds a " + redis.type(LOCK) + ": " + redis.hgetAll(LOCK));
            StringBuilder ttls = new StringBuilder();
            for (int i = 0; i < 8; i++) {
                Thread.sleep(500);
                ttls.append(redis.pttl(LOCK)).append(' ');
            }
            System.out.println("  PTTL every 500 ms for 4 s: " + ttls.toString().trim());
            lock.unlock();

            lock.lock(2, TimeUnit.SECONDS);                      // a fixed 2 s lease: no watchdog
            ttls.setLength(0);
            for (int i = 0; i < 6; i++) {
                Thread.sleep(500);
                ttls.append(redis.pttl(LOCK)).append(' ');
            }
            System.out.println("lock(2, SECONDS), no watchdog.");
            System.out.println("  PTTL every 500 ms for 3 s: " + ttls.toString().trim() + "   (-2: the key is gone)");
            System.out.println("  isHeldByCurrentThread() = " + lock.isHeldByCurrentThread());

            RFencedLock fenced = redisson.getFencedLock("demo:l08:fenced:settle");
            Long first = fenced.lockAndGetToken();
            fenced.unlock();
            Long second = fenced.lockAndGetToken();
            fenced.unlock();
            System.out.println("RFencedLock tokens for two acquisitions: " + first + ", " + second);
        } finally {
            redisson.shutdown();
        }
    }
}
