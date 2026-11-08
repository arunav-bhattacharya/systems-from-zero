package sfz.cache.l06.demo;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * A hot key on a simulated clock: about 10 reads a second, a recompute that takes 3 seconds, a TTL of 60.
 * How many recomputations does each refresh cost with a plain TTL, and with XFetch?
 */
public class XFetchDemo {
    static final double TTL = 60, DELTA = 3, RATE = 10, HOURS = 10;

    static void simulate(String label, double beta) {
        Random random = new Random(42);                      // same seed, same reads, in Java and Kotlin
        double expiry = TTL;                                 // the value was computed at t = 0
        List<Double> finishing = new ArrayList<>();          // recomputes in flight: when each one ends
        List<Integer> perRefresh = new ArrayList<>();        // recomputes started for each refresh
        int started = 0, misses = 0, recomputes = 0;
        double earlySum = 0;
        for (double t = 0; t < HOURS * 3600; t += -Math.log(1 - random.nextDouble()) / RATE) {
            for (int i = finishing.size() - 1; i >= 0; i--) {  // a finished recompute stores a fresh value
                if (finishing.get(i) <= t) {
                    double newExpiry = finishing.remove(i) + TTL;
                    if (newExpiry > expiry) {
                        expiry = newExpiry;
                        if (started > 0) perRefresh.add(started);
                        started = 0;
                    }
                }
            }
            boolean recompute;
            if (t >= expiry) {                               // nothing fresh to return: a miss
                misses++;
                recompute = true;
            } else if (beta > 0) {                           // XFetch: now - delta * beta * ln(rand) >= expiry
                double u = 1 - random.nextDouble();          // uniform in (0, 1]
                recompute = t - DELTA * beta * Math.log(u) >= expiry;
                if (recompute) earlySum += expiry - t;
            } else {
                recompute = false;
            }
            if (recompute) {
                started++;
                recomputes++;
                finishing.add(t + DELTA);
            }
        }
        double mean = perRefresh.stream().mapToInt(Integer::intValue).average().orElse(0);
        int max = perRefresh.stream().mapToInt(Integer::intValue).max().orElse(0);
        int early = recomputes - misses;
        System.out.printf("%-17s per refresh: %4.1f recomputes (max %2d)   reads that missed: %5d   recomputes per hour: %4.0f%s%n",
                label, mean, max, misses, recomputes / HOURS,
                early > 0 ? String.format("   started %.1f s early on average", earlySum / early) : "");
    }

    public static void main(String[] args) {
        System.out.printf("A hot key, %.0f hours: ~%.0f reads/s, %.0f s to recompute, TTL %.0f s%n", HOURS, RATE, DELTA, TTL);
        simulate("plain TTL", 0);
        simulate("XFetch, beta 1", 1);
        simulate("XFetch, beta 2", 2);
    }
}
