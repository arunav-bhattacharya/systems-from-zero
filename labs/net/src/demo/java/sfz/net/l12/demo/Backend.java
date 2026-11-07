package sfz.net.l12.demo;

import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;

/**
 * A backend for lesson 12: answers every request with its own name, the address the request came
 * from, and the X-Forwarded-For header, and logs the same line. With a delay it behaves like a slow
 * card issuer.
 *
 *   java Backend.java <port> <name> [delay-ms]
 *
 * In the lab box: java /labs/net/src/demo/java/sfz/net/l12/demo/Backend.java 8081 ledger-a &
 * The JDK's HttpServer keeps idle connections open for 30 s (-Dsun.net.httpserver.idleInterval=30).
 */
public class Backend {
    static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("HH:mm:ss");

    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(args[0]);
        String name = args.length > 1 ? args[1] : "backend";
        long delayMs = args.length > 2 ? Long.parseLong(args[2]) : 0;
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 100);
        server.createContext("/", ex -> {
            ex.getRequestBody().readAllBytes();
            String from = ex.getRemoteAddress().getAddress().getHostAddress() + ":" + ex.getRemoteAddress().getPort();
            String xff = ex.getRequestHeaders().getFirst("X-Forwarded-For");
            String line = String.format("%s %s %s from %s, X-Forwarded-For: %s", name, ex.getRequestMethod(),
                    ex.getRequestURI(), from, xff == null ? "(none)" : xff);
            try {
                Thread.sleep(delayMs);                    // the work
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            System.out.println(LocalTime.now().format(CLOCK) + "  " + line);
            byte[] body = (line + "\n").getBytes(StandardCharsets.UTF_8);
            ex.sendResponseHeaders(200, body.length);
            ex.getResponseBody().write(body);
            ex.close();
        });
        server.setExecutor(java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor());
        server.start();
        System.out.printf("%s listening on :%d%s%n", name, port, delayMs > 0 ? ", each answer takes " + delayMs + " ms" : "");
    }
}
