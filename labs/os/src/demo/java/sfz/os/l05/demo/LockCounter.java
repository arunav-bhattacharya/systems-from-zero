package sfz.os.l05.demo;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Threads add to one shared balance under a ReentrantLock. Run it under
 * {@code strace -f -c -e trace=futex} with 1 thread and with 4: the lock enters the
 * kernel only when threads collide. Argument: number of threads (default 1).
 */
public class LockCounter {
    static final ReentrantLock lock = new ReentrantLock();
    static long balance;

    public static void main(String[] args) throws Exception {
        int n = args.length > 0 ? Integer.parseInt(args[0]) : 1;
        int adds = 1_000_000;
        List<Thread> threads = new ArrayList<>();
        long t0 = System.nanoTime();
        for (int i = 0; i < n; i++) {
            threads.add(Thread.ofPlatform().name("depositor-" + i).start(() -> {
                for (int k = 0; k < adds; k++) {
                    lock.lock();            // a CAS in user space when nobody else holds it
                    try {
                        balance += 1;
                    } finally {
                        lock.unlock();      // unparks a waiter, if there is one
                    }
                }
            }));
        }
        for (Thread t : threads) t.join();
        System.out.printf("%d threads: balance = %,d in %d ms%n", n, balance, (System.nanoTime() - t0) / 1_000_000);
    }
}
