package sfz.dist.l04.demo;

/**
 * Lesson dist-04, section 3: a lease holder that can't see its own pauses. It holds a pretend 2-second lease and renews
 * it whenever less than 1 s is left. Every 100 ms it checks the lease, works for 80 ms, then "writes". The lease is a
 * deadline on the monotonic clock, so it runs out on time whether this process is running or not, exactly like a lease
 * kept by another machine.
 *
 * <p>It prints only when something unusual happens: a gap in its own loop, a lease that ran out, or a write made after
 * the lease ran out. Stop it from outside for a few seconds (docker pause, or kill -STOP from another shell) and resume
 * it. It ends by itself after 60 seconds.
 *
 * <p>Run in the lab box: java sim/src/demo/java/sfz/dist/l04/demo/PauseMeter.java
 */
public class PauseMeter {
    static long nowMs() {
        return System.nanoTime() / 1_000_000;            // monotonic: right for durations and deadlines (lesson 3)
    }

    public static void main(String[] args) throws InterruptedException {
        long start = nowMs();
        long leaseEnd = start + 2_000;
        long lastLoop = start;
        long lastWall = System.currentTimeMillis();
        int writes = 0;
        System.out.println("holding a 2 s lease; checking, working 80 ms and writing every 100 ms. Pause me now.");
        while (nowMs() - start < 60_000) {
            long t0 = nowMs();
            long wall = System.currentTimeMillis();
            if (t0 - lastLoop > 150) {
                System.out.printf("loop gap: %,d ms since the last turn (expected 100). The wall clock moved %,d ms.%n",
                        t0 - lastLoop, wall - lastWall);
            }
            lastLoop = t0;
            lastWall = wall;

            if (t0 >= leaseEnd) {                         // noticed only now, at the next check
                System.out.printf("lease lost: it ran out %,d ms ago. Taking a new one.%n", t0 - leaseEnd);
                leaseEnd = t0 + 2_000;
            } else if (leaseEnd - t0 < 1_000) {
                leaseEnd = t0 + 2_000;                    // renew
            }

            long left = leaseEnd - t0;                    // the check
            if (left > 0) {
                Thread.sleep(80);                         // the work: a pause here lands between check and write
                long t1 = nowMs();
                writes++;
                if (t1 >= leaseEnd) {
                    System.out.printf("STALE WRITE: checked with %,d ms left, wrote %,d ms after the lease ran out.%n",
                            left, t1 - leaseEnd);
                    leaseEnd = t1 + 2_000;                // the next turn would notice; start a new lease
                }
            }
            Thread.sleep(20);
        }
        System.out.printf("done: %,d writes in 60 s%n", writes);
    }
}
