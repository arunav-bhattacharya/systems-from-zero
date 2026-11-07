package sfz.net.l07.demo;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;

/**
 * Connects to each host:port it is given, the way JVM code does, with a 5-second connect timeout,
 * and prints how long each attempt took and how it ended. The point is the difference between
 * "Connection refused" (an RST came back at once), "Connect timed out" (the SYN got no answer at
 * all) and "No route to host" (nobody on the link answered ARP for that address).
 *
 * In env/net.yml (see the Try it in lesson 7):
 *   docker compose -f env/net.yml exec client java /labs/net/src/demo/java/sfz/net/l07/demo/Connect.java \
 *       10.10.1.20:9000 10.10.1.20:9001 10.10.1.20:9002 10.10.1.99:9000
 * With no arguments it tries a port it opens itself and a closed port, both on 127.0.0.1:
 *   ./gradlew :net:demo -Pmain=sfz.net.l07.demo.Connect      (from the labs folder)
 */
public class Connect {
    public static void main(String[] args) throws IOException {
        warmUp();
        if (args.length == 0) {
            try (ServerSocket open = new ServerSocket(0); ServerSocket closed = new ServerSocket(0)) {
                int closedPort = closed.getLocalPort();
                closed.close();                                     // free again, so nothing listens there
                tryConnect("127.0.0.1", open.getLocalPort());
                tryConnect("127.0.0.1", closedPort);
            }
            return;
        }
        for (String target : args) {
            int colon = target.lastIndexOf(':');
            tryConnect(target.substring(0, colon), Integer.parseInt(target.substring(colon + 1)));
        }
    }

    static void tryConnect(String host, int port) {
        long start = System.nanoTime();
        String result;
        try (Socket socket = new Socket()) {
            // connect() sends the SYN and returns when the SYN-ACK arrives (the kernel sends the ACK)
            socket.connect(new InetSocketAddress(host, port), 5_000);
            result = "connected from local port " + socket.getLocalPort();
        } catch (IOException e) {
            result = e.getClass().getSimpleName() + ": " + e.getMessage();
        }
        System.out.printf("%-17s %5d ms  %s%n", host + ":" + port, (System.nanoTime() - start) / 1_000_000, result);
    }

    /** One quiet connect on loopback first, so class loading doesn't count in the first timing. */
    static void warmUp() throws IOException {
        try (ServerSocket server = new ServerSocket(0); Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress("127.0.0.1", server.getLocalPort()), 1_000);
        }
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress("127.0.0.1", 1), 1_000);   // port 1: refused
        } catch (IOException expected) {
            // the exception classes are loaded now
        }
    }
}
