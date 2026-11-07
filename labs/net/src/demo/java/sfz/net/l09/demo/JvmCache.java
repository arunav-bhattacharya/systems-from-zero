package sfz.net.l09.demo;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.security.Security;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;

/**
 * Looks a name up through the JVM once a second, the way an HTTP client does before it connects,
 * and prints a line whenever the answer changes. It shows the JVM's own address cache: a copy of
 * every answer, kept for `networkaddress.cache.ttl` seconds (30 by default) whatever the DNS TTL.
 *
 * In the lab box, with the name in /etc/hosts and changed after 10 seconds (see lesson 9):
 *   java /labs/net/src/demo/java/sfz/net/l09/demo/JvmCache.java ledger.pay.test 40
 * Try it again with -Dsun.net.inetaddr.ttl=0 before the path: no cache at all.
 * On your Mac: ./gradlew :net:demo -Pmain=sfz.net.l09.demo.JvmCache -Pargs='example.com 5'
 */
public class JvmCache {
    static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("HH:mm:ss");

    public static void main(String[] args) throws Exception {
        String name = args.length > 0 ? args[0] : "example.com";
        int seconds = args.length > 1 ? Integer.parseInt(args[1]) : 40;
        System.out.println("networkaddress.cache.ttl = " + Security.getProperty("networkaddress.cache.ttl")
                + ", sun.net.inetaddr.ttl = " + System.getProperty("sun.net.inetaddr.ttl"));
        String last = null;
        for (int i = 0; i <= seconds; i++) {
            String now;
            try {
                now = InetAddress.getByName(name).getHostAddress();   // served from the JVM's cache when it can
            } catch (UnknownHostException e) {
                now = "unknown host";
            }
            if (!now.equals(last)) {
                System.out.printf("%s  t=%2d s  %s -> %s%n", LocalTime.now().format(CLOCK), i, name, now);
                last = now;
            }
            Thread.sleep(1_000);
        }
        System.out.println("done after " + seconds + " s");
    }
}
