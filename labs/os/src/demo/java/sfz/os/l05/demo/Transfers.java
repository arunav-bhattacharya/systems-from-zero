package sfz.os.l05.demo;

import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Two transfers between the same two accounts, in opposite directions.
 * Argument 1: "naive" locks source then target (deadlocks), "ordered" locks the smaller
 * account id first, "trylock" gives up the first lock when the second isn't free in time.
 * Argument 2: seconds to stay alive after a deadlock, so you can look at it (default 0).
 */
public class Transfers {
    static final class Account {
        final String id;
        final ReentrantLock lock = new ReentrantLock();     // used by the trylock mode only
        long balance;
        Account(String id, long balance) { this.id = id; this.balance = balance; }
    }

    static void transfer(Account from, Account to, long amount, String mode) throws InterruptedException {
        if (mode.equals("trylock")) {
            transferWithTryLock(from, to, amount);
            return;
        }
        Account first = from, second = to;
        if (mode.equals("ordered") && from.id.compareTo(to.id) > 0) { first = to; second = from; }  // smaller id first, always
        synchronized (first) {
            Thread.sleep(50);                                   // widen the window so the naive mode deadlocks every run
            synchronized (second) {
                from.balance -= amount;
                to.balance += amount;
            }
        }
    }

    static void transferWithTryLock(Account from, Account to, long amount) throws InterruptedException {
        int attempts = 0;
        while (true) {
            attempts++;
            from.lock.lock();
            try {
                Thread.sleep(50);
                if (to.lock.tryLock(10, TimeUnit.MILLISECONDS)) {     // wait a little, not forever
                    try {
                        from.balance -= amount;
                        to.balance += amount;
                        System.out.println(Thread.currentThread().getName() + " done after " + attempts + " attempt(s)");
                        return;
                    } finally {
                        to.lock.unlock();
                    }
                }
            } finally {
                from.lock.unlock();                                    // give back what we hold, then retry
            }
            Thread.sleep(ThreadLocalRandom.current().nextInt(1, 100));  // random back-off so the two don't collide again
        }
    }

    public static void main(String[] args) throws Exception {
        String mode = args.length > 0 ? args[0] : "naive";
        Account merchant = new Account("ACC-1001", 10_000);
        Account customer = new Account("ACC-2002", 500);
        Thread refund = Thread.ofPlatform().name("refund").start(() -> run(merchant, customer, 120, mode));
        Thread payment = Thread.ofPlatform().name("payment").start(() -> run(customer, merchant, 80, mode));
        System.out.println("pid " + ProcessHandle.current().pid() + ": " + mode + " locks");
        long deadline = System.currentTimeMillis() + 3_000;            // give both transfers 3 s in total
        refund.join(Math.max(1, deadline - System.currentTimeMillis()));
        payment.join(Math.max(1, deadline - System.currentTimeMillis()));
        if (refund.isAlive() || payment.isAlive()) {
            System.out.println("still waiting after 3 s: deadlock");
            Thread.sleep(Long.parseLong(args.length > 1 ? args[1] : "0") * 1000);
            System.exit(1);
        }
        System.out.println("merchant " + merchant.balance + ", customer " + customer.balance);
    }

    static void run(Account from, Account to, long amount, String mode) {
        try {
            transfer(from, to, amount, mode);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
