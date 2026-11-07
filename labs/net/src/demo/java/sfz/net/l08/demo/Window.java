package sfz.net.l08.demo;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;

/**
 * Sends bytes as fast as it can for 2 seconds over one TCP connection on 127.0.0.1, once for each
 * receive buffer size given (in KB; 0 means "let the kernel size it"), and prints the throughput the
 * receiver saw. The receive buffer caps the window the receiver can offer, and a sender can't have
 * more than one window of bytes in flight per round trip.
 *
 * Add delay first, or loopback's round trip is a few microseconds and the window hardly matters:
 *   tc qdisc add dev lo root netem delay 25ms        (each direction: a 50 ms round trip)
 * In the lab box:  java /labs/net/src/demo/java/sfz/net/l08/demo/Window.java 16 64 256 0
 * On your Mac:     ./gradlew :net:demo -Pmain=sfz.net.l08.demo.Window -Pargs='16 64 256 0'
 */
public class Window {
    public static void main(String[] args) throws Exception {
        String[] sizes = args.length > 0 ? args : new String[]{"16", "64", "256", "0"};
        for (String kb : sizes) {
            run(Integer.parseInt(kb));
        }
    }

    static void run(int receiveBufferKb) throws Exception {
        InetAddress lo = InetAddress.getByName("127.0.0.1");
        try (ServerSocket listener = new ServerSocket()) {
            // set before listen(): the window scale is agreed in the handshake, from this buffer size
            if (receiveBufferKb > 0) listener.setReceiveBufferSize(receiveBufferKb * 1024);
            listener.bind(new InetSocketAddress(lo, 0));
            Thread sender = Thread.ofPlatform().start(() -> send(lo, listener.getLocalPort()));
            try (Socket s = listener.accept(); InputStream in = s.getInputStream()) {
                byte[] buf = new byte[64 * 1024];
                long bytes = 0;
                long start = System.nanoTime();
                for (int n; (n = in.read(buf)) > 0; ) bytes += n;
                double seconds = (System.nanoTime() - start) / 1e9;
                System.out.printf("receive buffer %-8s %6.2f MB in %.1f s = %6.2f MB/s%n",
                        receiveBufferKb > 0 ? receiveBufferKb + " KB:" : "auto:", bytes / 1e6, seconds, bytes / 1e6 / seconds);
            }
            sender.join();
        }
    }

    static void send(InetAddress lo, int port) {
        byte[] chunk = new byte[64 * 1024];
        try (Socket s = new Socket(lo, port); OutputStream out = s.getOutputStream()) {
            long end = System.nanoTime() + 2_000_000_000L;
            while (System.nanoTime() < end) out.write(chunk);   // blocks whenever the window is full
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
