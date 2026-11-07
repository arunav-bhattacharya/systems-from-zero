package sfz.net.l12.demo;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;

/**
 * A payment service's outbound calls: one long-lived JDK HttpClient (so one connection pool), sending
 * requests at fixed moments and printing what happened to each.
 *
 *   java Caller.java <url> <GET|POST> <seconds,seconds,...>
 *
 * For example `java Caller.java http://127.0.0.1:8080/authorize POST 0,2,9` sends a POST at once,
 * another 2 s later and a third 9 s after the start. The pool keeps idle connections for
 * -Djdk.httpclient.keepalive.timeout seconds (30 by default).
 * In the lab box: java /labs/net/src/demo/java/sfz/net/l12/demo/Caller.java ...
 */
public class Caller {
    static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("HH:mm:ss");

    public static void main(String[] args) throws Exception {
        URI uri = URI.create(args[0]);
        String method = args[1];
        HttpClient client = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(2))
                .build();
        System.out.println("pool idle timeout: " + System.getProperty("jdk.httpclient.keepalive.timeout", "30 (the default)") + " s");
        long start = System.nanoTime();
        for (String at : args[2].split(",")) {
            long due = start + (long) (Double.parseDouble(at) * 1e9);
            Thread.sleep(Math.max(0, (due - System.nanoTime()) / 1_000_000));
            HttpRequest req = HttpRequest.newBuilder(uri)
                    .method(method, method.equals("POST") ? HttpRequest.BodyPublishers.ofString("{\"amount\":\"100.00\"}") : HttpRequest.BodyPublishers.noBody())
                    .timeout(Duration.ofSeconds(5))
                    .build();
            String t = String.format("%s  t=%4.1f s  %s", LocalTime.now().format(CLOCK), (System.nanoTime() - start) / 1e9, method);
            try {
                HttpResponse<String> r = client.send(req, HttpResponse.BodyHandlers.ofString());
                System.out.println(t + "  " + r.statusCode() + "  " + r.body().strip());
            } catch (Exception e) {
                Throwable root = e;
                while (root.getCause() != null) root = root.getCause();
                System.out.println(t + "  failed: " + e.getClass().getSimpleName() + ": " + e.getMessage()
                        + (root != e ? " (" + root.getClass().getSimpleName() + ": " + root.getMessage() + ")" : ""));
            }
        }
    }
}
