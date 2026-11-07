package sfz.net.l12.demo;

import java.util.PriorityQueue;
import java.util.Random;

/**
 * A simulation of a retry storm (lesson 12). 1,000 clients send a request at t = 0. The issuer is
 * down until t = 250 ms, and after that it can answer 100 requests in each 10 ms (10,000 a second);
 * a request beyond that fails. Every failed client retries with exponential backoff: it waits up to
 * 100 ms, then 200, 400, 800, capped at 1 s, and gives up after 6 attempts.
 *
 * Without jitter every client waits exactly the same time, so the retries arrive in the same 10 ms
 * and most of them fail again. With full jitter each waits a random time between 0 and that ceiling.
 * The table shows, for each 100 ms, how many requests arrived and how many were answered.
 *   java Jitter.java
 * In the lab box: java /labs/net/src/demo/java/sfz/net/l12/demo/Jitter.java
 */
public class Jitter {
    static final int CLIENTS = 1_000, MAX_ATTEMPTS = 6, PER_SLOT = 100, SLOT_MS = 10;
    static final long BASE_MS = 100, CAP_MS = 1_000, DOWN_UNTIL_MS = 250, SHOW_MS = 2_000;

    public static void main(String[] args) {
        for (boolean jitter : new boolean[]{false, true}) run(jitter);
    }

    static void run(boolean jitter) {
        Random random = new Random(42);                                   // the same numbers every run
        PriorityQueue<long[]> due = new PriorityQueue<>((a, b) -> Long.compare(a[0], b[0]));   // {time, client, attempt}
        for (int c = 0; c < CLIENTS; c++) due.add(new long[]{0, c, 1});
        int[] slotUse = new int[100_000];
        int[] arrived = new int[(int) (SHOW_MS / 100)], answered = new int[arrived.length];
        int[] retriesInSlot = new int[100_000];
        int ok = 0, requests = 0, busiest = 0;
        long lastOk = 0;
        while (!due.isEmpty()) {
            long[] r = due.poll();
            long t = r[0];
            int slot = (int) (t / SLOT_MS);
            requests++;
            slotUse[slot]++;
            if (r[2] > 1) busiest = Math.max(busiest, ++retriesInSlot[slot]);       // retries only, not the first try
            boolean served = t >= DOWN_UNTIL_MS && slotUse[slot] <= PER_SLOT;
            if (t < SHOW_MS) {
                arrived[(int) (t / 100)]++;
                if (served) answered[(int) (t / 100)]++;
            }
            if (served) {
                ok++;
                lastOk = t;
            } else if (r[2] < MAX_ATTEMPTS) {
                long ceiling = Math.min(CAP_MS, BASE_MS << (r[2] - 1));     // 100, 200, 400, 800, 1000 ms
                long wait = jitter ? (long) (random.nextDouble() * ceiling) : ceiling;
                due.add(new long[]{t + wait, r[1], r[2] + 1});
            }
        }
        System.out.println(jitter ? "full jitter: wait random(0, min(1 s, 100 ms x 2^n))" : "no jitter: wait min(1 s, 100 ms x 2^n)");
        System.out.println("     ms  arrived  answered");
        for (int i = 0; i < arrived.length; i++) {
            if (arrived[i] > 0) System.out.printf("  %5d  %7d  %8d%n", i * 100, arrived[i], answered[i]);
        }
        System.out.printf("  answered %d of %d clients, the last at %d ms; %d requests in all; busiest 10 ms: %d retries%n%n",
                ok, CLIENTS, lastOk, requests, busiest);
    }
}
