package sfz.os.l03.demo;

import java.util.concurrent.Executors;

/**
 * A small "service" with named threads to find from outside the JVM:
 * two ledger writers that sleep, one fraud scorer that burns CPU, and
 * 1,000 virtual threads that wait on a pretend card-issuer call.
 *
 * <p>Run it in the background in the lab box, then look at it with
 * {@code ls /proc/<pid>/task}, {@code ps -L} and {@code jstack}.
 */
public class PaymentWorkers {
    public static void main(String[] args) throws Exception {
        for (int i = 1; i <= 2; i++) {
            Thread.ofPlatform().name("ledger-writer-" + i).start(PaymentWorkers::sleepForever);
        }
        Thread.ofPlatform().name("fraud-scorer").start(PaymentWorkers::score);

        var issuerCalls = Executors.newVirtualThreadPerTaskExecutor();
        for (int i = 0; i < 1_000; i++) {
            issuerCalls.submit(() -> {
                Thread.sleep(120_000);           // a virtual thread waiting gives back its carrier
                return null;
            });
        }
        System.out.println("pid " + ProcessHandle.current().pid() + " running");
        Thread.sleep(Long.parseLong(args.length > 0 ? args[0] : "60") * 1000);
        System.exit(0);
    }

    static void sleepForever() {
        try {
            Thread.sleep(Long.MAX_VALUE);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    // a busy loop: this is the thread that shows up hot in top -H
    static void score() {
        long h = 17;
        while (true) {
            h = h * 31 + System.nanoTime();
            if (h == 42) System.out.println("unlikely");
        }
    }
}
