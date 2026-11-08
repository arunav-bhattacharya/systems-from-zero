package sfz.msg.l01.demo;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * 1,000 payment events for 10 accounts go through a broker queue, in memory, with no threads and no randomness.
 * Consumers take 1 to 3 ticks per message. A crashing consumer dies just after finishing a message and before its
 * ack, every N ticks (25 unless you pass another number), and comes back 5 ticks later.
 * For each setup the demo counts redeliveries, duplicates, per-account inversions and lost messages.
 */
public class RedeliveryDemo {
    record Message(String key, int seq) {}

    record Delivery(long tag, Message message, boolean redelivered) {}

    /** A queue with acks, prefetch and redelivery to the original position. */
    static final class Queue {
        record Entry(long position, Message message, int returns) {}

        record InFlight(Entry entry, String consumer) {}

        final TreeMap<Long, Entry> waiting = new TreeMap<>();
        final LinkedHashMap<Long, InFlight> inFlight = new LinkedHashMap<>();
        final Map<String, Integer> prefetch = new HashMap<>();
        final Set<String> autoAck = new HashSet<>();
        long nextPosition = 0, nextTag = 1;

        void publish(Message m) {
            waiting.put(nextPosition, new Entry(nextPosition, m, 0));
            nextPosition++;
        }

        void subscribe(String c, int max, boolean auto) {
            prefetch.put(c, max);
            if (auto) autoAck.add(c);
        }

        Delivery deliver(String c) {
            boolean auto = autoAck.contains(c);
            long held = inFlight.values().stream().filter(f -> f.consumer().equals(c)).count();
            if (!auto && held >= prefetch.get(c)) return null;          // at its prefetch
            var head = waiting.pollFirstEntry();
            if (head == null) return null;
            long tag = nextTag++;
            if (!auto) inFlight.put(tag, new InFlight(head.getValue(), c));
            return new Delivery(tag, head.getValue().message(), head.getValue().returns() > 0);
        }

        void ack(long tag) {
            inFlight.remove(tag);
        }

        void disconnect(String c) {
            List<Long> tags = inFlight.entrySet().stream().filter(e -> e.getValue().consumer().equals(c)).map(Map.Entry::getKey).toList();
            for (long tag : tags) {
                Entry e = inFlight.remove(tag).entry();
                waiting.put(e.position(), new Entry(e.position(), e.message(), e.returns() + 1));   // back to its old place
            }
        }
    }

    /** Consumers on one queue, one tick at a time. */
    static final class Sim {
        final Queue q;
        final List<String> names;
        final int prefetch;
        final boolean auto;
        final List<Message> booked = new ArrayList<>();
        final Map<String, ArrayDeque<Delivery>> held = new HashMap<>();
        final Map<String, Delivery> working = new HashMap<>();
        final Map<String, Integer> ticksLeft = new HashMap<>();
        final Map<String, Integer> down = new HashMap<>();
        int redelivered = 0;

        Sim(Queue q, List<String> names, int prefetch, boolean auto) {
            this.q = q;
            this.names = names;
            this.prefetch = prefetch;
            this.auto = auto;
            for (String c : names) {
                held.put(c, new ArrayDeque<>());
                q.subscribe(c, prefetch, auto);
            }
        }

        static int cost(Message m) {
            return 1 + Math.floorMod(m.seq() * 7 + m.key().hashCode(), 3);
        }

        void tick() {
            for (String c : names) {
                Integer wait = down.get(c);
                if (wait != null) {
                    if (wait > 1) down.put(c, wait - 1);
                    else down.remove(c);
                    continue;
                }
                ArrayDeque<Delivery> mine = held.get(c);
                while (mine.size() + (working.containsKey(c) ? 1 : 0) < prefetch) {
                    Delivery d = q.deliver(c);
                    if (d == null) break;
                    if (d.redelivered()) redelivered++;
                    mine.addLast(d);
                }
                if (!working.containsKey(c)) {
                    Delivery next = mine.pollFirst();
                    if (next == null) continue;
                    working.put(c, next);
                    ticksLeft.put(c, cost(next.message()));
                }
                int left = ticksLeft.merge(c, -1, Integer::sum);
                if (left == 0) {
                    Delivery done = working.remove(c);
                    booked.add(done.message());
                    if (!auto) q.ack(done.tag());
                }
            }
        }

        void crash(String c) {
            if (down.containsKey(c)) return;
            Delivery current = working.remove(c);
            if (current != null) booked.add(current.message());     // the work is done, the ack is lost
            held.get(c).clear();
            q.disconnect(c);
            down.put(c, 5);                                         // back in 5 ticks
        }

        void run(String crashing, int every) {
            int t = 0;
            while (!q.waiting.isEmpty() || !q.inFlight.isEmpty() || !working.isEmpty() || !down.isEmpty()
                    || held.values().stream().anyMatch(h -> !h.isEmpty())) {
                t++;
                if (crashing != null && every > 0 && t % every == 0) crash(crashing);
                tick();
            }
        }
    }

    static List<Message> payments() {
        List<Message> out = new ArrayList<>();
        for (int i = 0; i < 1000; i++) out.add(new Message("acct-" + i % 10, i / 10));
        return out;
    }

    /** The row: booked, redelivered, duplicates, inversions, lost. */
    static void row(String setup, List<Message> booked, int redelivered) {
        Set<Message> seen = new HashSet<>();
        Map<String, Integer> highest = new HashMap<>();
        int duplicates = 0, inversions = 0;
        for (Message m : booked) {
            if (!seen.add(m)) {
                duplicates++;
                continue;
            }
            Integer top = highest.get(m.key());
            if (top != null && m.seq() < top) inversions++;
            else highest.put(m.key(), m.seq());
        }
        System.out.printf("%-38s %6d %11d %10d %10d %5d%n", setup, booked.size(), redelivered, duplicates, inversions, 1000 - seen.size());
    }

    static void oneQueue(String setup, List<String> consumers, int prefetch, boolean auto, int every) {
        Queue q = new Queue();
        payments().forEach(q::publish);
        Sim sim = new Sim(q, consumers, prefetch, auto);
        sim.run(consumers.get(consumers.size() - 1), every);
        row(setup, sim.booked, sim.redelivered);
    }

    public static void main(String[] args) {
        int every = args.length > 0 ? Integer.parseInt(args[0]) : 25;
        System.out.printf("1,000 payments, 10 accounts; a crash every %d ticks%n", every);
        System.out.printf("%-38s %6s %11s %10s %10s %5s%n", "setup", "booked", "redelivered", "duplicates", "inversions", "lost");
        oneQueue("1 consumer,  prefetch 10, no crash", List.of("A"), 10, false, 0);
        oneQueue("1 consumer,  prefetch 10, crashes", List.of("A"), 10, false, every);
        oneQueue("2 consumers, prefetch 1,  crashes", List.of("A", "B"), 1, false, every);
        oneQueue("2 consumers, prefetch 10, no crash", List.of("A", "B"), 10, false, 0);
        oneQueue("2 consumers, prefetch 10, crashes", List.of("A", "B"), 10, false, every);
        oneQueue("2 consumers, prefetch 100, crashes", List.of("A", "B"), 100, false, every);
        oneQueue("1 consumer,  auto-ack, crashes", List.of("A"), 10, true, every);

        // one queue per half of the accounts, one consumer each: the way a log's partitions work
        Queue even = new Queue(), odd = new Queue();
        for (Message m : payments()) (Integer.parseInt(m.key().substring(5)) % 2 == 0 ? even : odd).publish(m);
        Sim a = new Sim(even, List.of("A"), 10, false), b = new Sim(odd, List.of("B"), 10, false);
        a.run("A", every);
        b.run("B", every);
        List<Message> both = new ArrayList<>(a.booked);
        both.addAll(b.booked);
        row("2 queues by account, 1 consumer each", both, a.redelivered + b.redelivered);
    }
}
