package sfz.net.l08.demo;

import java.io.DataInputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.Arrays;

/**
 * The write-write-read pattern that Nagle's algorithm and delayed ACKs turn into a stall.
 *
 * A client sends 50 authorization requests over one connection on 127.0.0.1. Each request is two
 * writes, a 12-byte header and then a 100-byte body, and the client then reads a 2-byte reply. The
 * server replies only once it has the whole request. Run once with Nagle on (the JVM default) and
 * once with TCP_NODELAY, and compare the latency of each request.
 *
 * In the lab box:  java /labs/net/src/demo/java/sfz/net/l08/demo/Nagle.java
 * On your Mac:     ./gradlew :net:demo -Pmain=sfz.net.l08.demo.Nagle
 */
public class Nagle {
    static final int REQUESTS = 50;

    public static void main(String[] args) throws Exception {
        run(false);
        run(true);
    }

    static void run(boolean noDelay) throws Exception {
        InetAddress lo = InetAddress.getByName("127.0.0.1");
        try (ServerSocket listener = new ServerSocket(0, 50, lo)) {
            Thread server = Thread.ofPlatform().start(() -> serve(listener));
            long[] micros = new long[REQUESTS];
            try (Socket s = new Socket(lo, listener.getLocalPort())) {
                s.setTcpNoDelay(noDelay);                       // false: Nagle's algorithm is on
                OutputStream out = s.getOutputStream();
                InputStream in = s.getInputStream();
                byte[] header = new byte[12], body = new byte[100], reply = new byte[2];
                for (int i = 0; i < REQUESTS; i++) {
                    long start = System.nanoTime();
                    out.write(header);                          // write 1: goes out at once
                    out.write(body);                            // write 2: Nagle may hold it back
                    new DataInputStream(in).readFully(reply);   // read: wait for the server's reply
                    micros[i] = (System.nanoTime() - start) / 1_000;
                }
            }
            server.join();
            long[] sorted = micros.clone();
            Arrays.sort(sorted);
            System.out.printf("TCP_NODELAY %-5s median %6.2f ms   slowest %6.2f ms   all 50 took %5d ms%n",
                    noDelay, sorted[REQUESTS / 2] / 1000.0, sorted[REQUESTS - 1] / 1000.0, Arrays.stream(micros).sum() / 1000);
        }
    }

    static void serve(ServerSocket listener) {
        try (Socket s = listener.accept()) {
            DataInputStream in = new DataInputStream(s.getInputStream());
            OutputStream out = s.getOutputStream();
            byte[] request = new byte[112];
            for (int i = 0; i < REQUESTS; i++) {
                in.readFully(request);                          // the whole request: header and body
                out.write(new byte[]{'O', 'K'});
            }
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
