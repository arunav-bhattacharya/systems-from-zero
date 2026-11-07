package sfz.net.l12.demo;

import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.TimeUnit;

/**
 * Four calls, four different ways to wait, and which timeout stops each one (lesson 12).
 *
 * It starts its own server on 127.0.0.1 that misbehaves in two ways: "/slow" answers after 3 s, and
 * "/trickle" sends its headers at once and then one byte of body every 500 ms, 20 bytes in all.
 * The JDK HttpClient has a connect timeout and a request timeout; the request timeout stops waiting
 * for the response headers, not for the body.
 *
 *   java Timeouts.java [blackhole-address]          default 10.255.255.1, an address nobody answers
 *
 * In the lab box: java /labs/net/src/demo/java/sfz/net/l12/demo/Timeouts.java
 */
public class Timeouts {

    public static void main(String[] args) throws Exception {
        String blackhole = args.length > 0 ? args[0] : "10.255.255.1";
        ServerSocket listener = new ServerSocket(0, 50, InetAddress.getLoopbackAddress());
        Thread.ofVirtual().start(() -> serve(listener));
        String base = "http://127.0.0.1:" + listener.getLocalPort();

        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(1)).build();
        Duration requestTimeout = Duration.ofSeconds(1);

        time("1. connect to a silent address", () -> client.send(
                HttpRequest.newBuilder(URI.create("http://" + blackhole + "/")).timeout(requestTimeout).build(),
                HttpResponse.BodyHandlers.ofString()));
        time("2. a server that takes 3 s to answer", () -> client.send(
                HttpRequest.newBuilder(URI.create(base + "/slow")).timeout(requestTimeout).build(),
                HttpResponse.BodyHandlers.ofString()));
        time("3. a body that trickles in", () -> client.send(
                HttpRequest.newBuilder(URI.create(base + "/trickle")).timeout(requestTimeout).build(),
                HttpResponse.BodyHandlers.ofString()));
        time("4. the same, with a 2 s deadline", () -> client.sendAsync(
                HttpRequest.newBuilder(URI.create(base + "/trickle")).timeout(requestTimeout).build(),
                HttpResponse.BodyHandlers.ofString()).orTimeout(2, TimeUnit.SECONDS).get());
        System.exit(0);
    }

    interface Call { HttpResponse<String> run() throws Exception; }

    static void time(String what, Call call) {
        long start = System.nanoTime();
        String outcome;
        try {
            HttpResponse<String> r = call.run();
            outcome = r.statusCode() + ", " + r.body().length() + " bytes of body";
        } catch (Exception e) {
            Throwable t = e.getCause() != null && e instanceof java.util.concurrent.ExecutionException ? e.getCause() : e;
            outcome = t.getClass().getSimpleName() + ": " + t.getMessage();
        }
        System.out.printf("%-38s %5.1f s  %s%n", what, (System.nanoTime() - start) / 1e9, outcome);
    }

    static void serve(ServerSocket listener) {
        while (true) {
            try {
                Socket s = listener.accept();
                Thread.ofVirtual().start(() -> {
                    try (s) {
                        String request = new String(s.getInputStream().readNBytes(16), StandardCharsets.US_ASCII);
                        OutputStream out = s.getOutputStream();
                        if (request.contains("/slow")) {
                            Thread.sleep(3_000);                                  // nothing at all for 3 s
                            out.write("HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok".getBytes(StandardCharsets.US_ASCII));
                        } else {
                            out.write("HTTP/1.1 200 OK\r\nContent-Length: 20\r\n\r\n".getBytes(StandardCharsets.US_ASCII));
                            out.flush();
                            for (int i = 0; i < 20; i++) {                        // headers at once, then a byte every 500 ms
                                Thread.sleep(500);
                                out.write('.');
                                out.flush();
                            }
                        }
                        out.flush();
                        s.getInputStream().read();                                // wait for the client to hang up
                    } catch (Exception e) {
                        // the client gave up
                    }
                });
            } catch (Exception e) {
                return;
            }
        }
    }
}
