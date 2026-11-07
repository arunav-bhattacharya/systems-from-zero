package sfz.os.l04.demo;

import java.lang.management.ManagementFactory;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Busy threads under a CPU quota. Each thread does tiny units of work in a loop and
 * measures the gap between two units. A gap longer than 10 ms is a stall: the thread
 * was runnable and wanted the CPU, and didn't get it.
 *
 * <p>Run it in a container with {@code --cpus=0.5} and compare with no limit.
 * Arguments: number of threads (default 4), seconds to run (default 2).
 */
public class CpuQuota {
    static volatile boolean stop;

    public static void main(String[] args) throws Exception {
        int threads = args.length > 0 ? Integer.parseInt(args[0]) : 4;
        long seconds = args.length > 1 ? Long.parseLong(args[1]) : 2;
        System.out.println("availableProcessors() = " + Runtime.getRuntime().availableProcessors());

        AtomicLong stalls = new AtomicLong();
        AtomicLong longestNs = new AtomicLong();
        List<Thread> workers = new ArrayList<>();
        for (int i = 0; i < threads; i++) {
            workers.add(Thread.ofPlatform().name("scorer-" + i).start(() -> {
                long prev = System.nanoTime();
                long h = 17;
                while (!stop) {
                    for (int k = 0; k < 2_000; k++) h = h * 31 + k;   // a few microseconds of CPU
                    long now = System.nanoTime();
                    long gap = now - prev;
                    if (gap > 10_000_000) stalls.incrementAndGet();      // runnable, but not running
                    longestNs.accumulateAndGet(gap, Math::max);
                    prev = now;
                }
                if (h == 42) System.out.println("unlikely");
            }));
        }

        var os = (com.sun.management.OperatingSystemMXBean) ManagementFactory.getOperatingSystemMXBean();
        long cpu0 = os.getProcessCpuTime();
        long t0 = System.nanoTime();
        Thread.sleep(seconds * 1000);
        stop = true;
        for (Thread t : workers) t.join();
        double wall = (System.nanoTime() - t0) / 1e9;
        double cpu = (os.getProcessCpuTime() - cpu0) / 1e9;

        System.out.printf("%d busy threads for %.1f s used %.1f s of CPU%n", threads, wall, cpu);
        System.out.printf("stalls over 10 ms: %d, longest %.0f ms%n", stalls.get(), longestNs.get() / 1e6);
    }
}
