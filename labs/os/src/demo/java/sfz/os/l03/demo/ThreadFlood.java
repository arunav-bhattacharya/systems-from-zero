package sfz.os.l03.demo;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;

/**
 * Starts N threads that each wait 3 seconds, like N requests waiting on a slow card issuer.
 *
 * <p>Usage: {@code java ThreadFlood.java platform 200} or {@code java ThreadFlood.java virtual 10000}.
 * Run it in a container with {@code --pids-limit 64} to watch platform threads hit the limit.
 */
public class ThreadFlood {
    public static void main(String[] args) throws Exception {
        boolean virtual = args.length > 0 && args[0].equals("virtual");
        int n = args.length > 1 ? Integer.parseInt(args[1]) : 200;
        CountDownLatch release = new CountDownLatch(1);
        Runnable waitForIssuer = () -> {
            try {
                release.await();                       // blocks: a platform thread holds its OS thread here
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        };

        List<Thread> started = new ArrayList<>();
        try {
            for (int i = 0; i < n; i++) {
                started.add(virtual ? Thread.ofVirtual().start(waitForIssuer)
                                    : Thread.ofPlatform().start(waitForIssuer));
            }
            System.out.printf("started %,d %s threads%n", started.size(), virtual ? "virtual" : "platform");
        } catch (OutOfMemoryError e) {                 // what the JVM throws when clone() fails
            System.out.printf("failed after %,d %s threads: %s%n",
                    started.size(), virtual ? "virtual" : "platform", e.getMessage());
        }
        System.out.println("OS threads in this JVM: " + osThreads());
        Thread.sleep(3_000);
        release.countDown();
        for (Thread t : started) t.join();
    }

    // the kernel's count of tasks in this process, from /proc/self/status (Linux only)
    static String osThreads() throws Exception {
        Path status = Path.of("/proc/self/status");
        if (!Files.exists(status)) return "unknown (no /proc on this OS)";
        return Files.readAllLines(status).stream()
                .filter(l -> l.startsWith("Threads:"))
                .map(l -> l.substring("Threads:".length()).trim())
                .findFirst().orElse("?");
    }
}
