package sfz.net.l05.demo;

import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;

/**
 * Resolves a name the way a JVM service does, prints every address in the order the JVM returns them,
 * then connects the way most JVM code does: to the first address only, with a 3-second timeout.
 *
 * Run it on `app` in env/net.yml (the lab box image has JDK 25, and a single Java file runs without Gradle):
 *   docker compose -f env/net.yml exec app java /labs/net/src/demo/java/sfz/net/l05/demo/Dial.java api 8080
 * Add -Djava.net.preferIPv6Addresses=true before the path to put IPv6 addresses first.
 */
public class Dial {
    public static void main(String[] args) throws Exception {
        String host = args.length > 0 ? args[0] : "api";
        int port = args.length > 1 ? Integer.parseInt(args[1]) : 8080;

        // every address the resolver returned, in the JVM's order (IPv4 first unless told otherwise)
        for (InetAddress a : InetAddress.getAllByName(host)) {
            System.out.println("resolved  " + a.getHostAddress());
        }

        // new InetSocketAddress(host, port) keeps only the FIRST address: no second try, no race
        InetSocketAddress target = new InetSocketAddress(host, port);
        long start = System.nanoTime();
        try (Socket socket = new Socket()) {
            socket.connect(target, 3_000);
            System.out.printf("connected to %s in %d ms%n", socket.getInetAddress().getHostAddress(), (System.nanoTime() - start) / 1_000_000);
        } catch (Exception e) {
            System.out.printf("%s after %d ms (tried only %s)%n", e, (System.nanoTime() - start) / 1_000_000, target.getAddress().getHostAddress());
        }
    }
}
