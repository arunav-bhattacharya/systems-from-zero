package sfz.os.l08.demo;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.Deflater;

/**
 * Native memory churn the Java heap never sees. Each Deflater's zlib state is about 260 KB
 * of malloc'd memory. Threads take turns: create 64 Deflaters, end 63 of them, keep one.
 * Arguments: threads (default 16), seconds to stay alive at the end (default 0).
 */
public class NativeChurn {
    static final int PER_THREAD = 64;
    static int turn = 0;

    public static void main(String[] args) throws Exception {
        int threads = args.length > 0 ? Integer.parseInt(args[0]) : 16;
        int stay = args.length > 1 ? Integer.parseInt(args[1]) : 0;
        System.out.printf("pid %d, MALLOC_ARENA_MAX=%s, RSS at start %d MB%n",
                ProcessHandle.current().pid(), System.getenv().getOrDefault("MALLOC_ARENA_MAX", "(unset)"), rssMb());
        Object lock = new Object();
        List<Deflater> kept = new ArrayList<>();
        List<Thread> workers = new ArrayList<>();
        byte[] input = new byte[64 << 10];
        for (int t = 0; t < threads; t++) {
            int id = t;
            Thread w = new Thread(() -> {
                synchronized (lock) {
                    while (turn != id) {
                        try { lock.wait(); } catch (InterruptedException e) { return; }
                    }
                    List<Deflater> mine = new ArrayList<>();
                    byte[] out = new byte[1 << 10];
                    for (int i = 0; i < PER_THREAD; i++) {
                        Deflater d = new Deflater(6);             // zlib mallocs its state in this thread
                        d.setInput(input);
                        d.deflate(out);
                        mine.add(d);
                    }
                    for (int i = 0; i < PER_THREAD - 1; i++) mine.get(i).end();   // free() all but the last
                    kept.add(mine.get(PER_THREAD - 1));
                    turn++;
                    lock.notifyAll();
                }
            }, "worker-" + t);
            workers.add(w);
            w.start();
        }
        for (Thread w : workers) w.join();
        System.out.printf("%d threads made %d Deflaters and ended all but %d: RSS %d MB%n",
                threads, threads * PER_THREAD, kept.size(), rssMb());
        Thread.sleep(stay * 1000L);
        kept.forEach(Deflater::end);
    }

    static long rssMb() throws Exception {
        for (String line : Files.readAllLines(Path.of("/proc/self/status")))
            if (line.startsWith("VmRSS:")) return Long.parseLong(line.replaceAll("[^0-9]", "")) / 1024;
        return -1;
    }
}
