package sfz.cache.l01.demo;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Random;

/** Measures four rungs of the latency ladder from the JVM: CPU cache, RAM, the OS page cache, a loopback round trip. */
public class LatencyDemo {
    public static void main(String[] args) throws Exception {
        System.out.printf("pointer chase, 16 KB array (fits in the L1 cache): %8.1f ns per load%n", chase(16 << 10, 50_000_000));
        System.out.printf("pointer chase, 4 MB array (an L2 or L3 cache):     %8.1f ns per load%n", chase(4 << 20, 20_000_000));
        System.out.printf("pointer chase, 256 MB array (main memory):         %8.1f ns per load%n", chase(256 << 20, 10_000_000));
        System.out.printf("4 KB read from a file the OS has cached:           %8.1f us per read%n", cachedFileRead() / 1_000);
        System.out.printf("1-byte round trip over loopback TCP:               %8.1f us per round trip%n", loopbackRoundTrip() / 1_000);
    }

    /** Follows a random cycle through an int array, so every load depends on the one before: no prefetching helps. */
    static double chase(int bytes, int steps) {
        int n = bytes / 4;
        int[] next = new int[n];
        for (int i = 0; i < n; i++) next[i] = i;
        Random random = new Random(1);
        for (int i = n - 1; i > 0; i--) {                 // Sattolo's shuffle: one cycle through every slot
            int j = random.nextInt(i);
            int t = next[i]; next[i] = next[j]; next[j] = t;
        }
        int p = 0;
        for (int i = 0; i < steps / 10; i++) p = next[p];  // warm up the JIT and the caches
        long t0 = System.nanoTime();
        for (int i = 0; i < steps; i++) p = next[p];
        long ns = System.nanoTime() - t0;
        if (p == -1) System.out.println();                // use p, so the JIT can't drop the loop
        return (double) ns / steps;
    }

    /** Random 4 KB reads from a 64 MB file that was just written, so every block sits in the page cache. */
    static double cachedFileRead() throws IOException {
        Path file = Files.createTempFile("sfz-ladder", ".bin");
        try {
            Files.write(file, new byte[64 << 20]);
            try (FileChannel ch = FileChannel.open(file, StandardOpenOption.READ)) {
                ByteBuffer buf = ByteBuffer.allocateDirect(4096);
                Random random = new Random(2);
                int blocks = (64 << 20) / 4096;
                for (int i = 0; i < 20_000; i++) { buf.clear(); ch.read(buf, (long) random.nextInt(blocks) * 4096); }
                int reads = 200_000;
                long t0 = System.nanoTime();
                for (int i = 0; i < reads; i++) { buf.clear(); ch.read(buf, (long) random.nextInt(blocks) * 4096); }
                return (double) (System.nanoTime() - t0) / reads;
            }
        } finally {
            Files.delete(file);
        }
    }

    /** One byte to an echo server on the same machine and back: two trips through the kernel's network stack. */
    static double loopbackRoundTrip() throws Exception {
        try (ServerSocket server = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
            Thread echo = new Thread(() -> {
                try (Socket s = server.accept(); InputStream in = s.getInputStream(); OutputStream out = s.getOutputStream()) {
                    int b;
                    while ((b = in.read()) != -1) out.write(b);
                } catch (IOException ignored) {
                }
            });
            echo.start();
            try (Socket client = new Socket(InetAddress.getLoopbackAddress(), server.getLocalPort())) {
                client.setTcpNoDelay(true);
                InputStream in = client.getInputStream();
                OutputStream out = client.getOutputStream();
                for (int i = 0; i < 5_000; i++) { out.write(1); in.read(); }
                int trips = 20_000;
                long t0 = System.nanoTime();
                for (int i = 0; i < trips; i++) { out.write(1); in.read(); }
                return (double) (System.nanoTime() - t0) / trips;
            } finally {
                echo.join(1_000);
            }
        }
    }
}
