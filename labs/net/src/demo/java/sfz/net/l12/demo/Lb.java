package sfz.net.l12.demo;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/**
 * A load balancer in two modes, for lesson 12.
 *
 *   java Lb.java l4 <port> <backend,backend...> [idle-seconds]
 *       Copies bytes between each client connection and a backend connection, picking backends in
 *       turn. It never reads HTTP. With idle-seconds it behaves like a cloud network load balancer: a
 *       connection with no traffic for that long is forgotten (the backend side is closed), and when
 *       the client sends anything on it later, the client gets a TCP reset.
 *   java Lb.java l7 <port> <backend,backend...>
 *       Reads each HTTP request, adds X-Forwarded-For with the client's address, and sends it to a
 *       backend over the balancer's own pooled connections.
 *
 * Backends are host:port, for example 127.0.0.1:8081,127.0.0.1:8082.
 * In the lab box: java /labs/net/src/demo/java/sfz/net/l12/demo/Lb.java l4 8080 127.0.0.1:8081 5 &
 */
public class Lb {
    static final DateTimeFormatter CLOCK = DateTimeFormatter.ofPattern("HH:mm:ss");
    static final AtomicInteger NEXT = new AtomicInteger();
    static List<String> backends;

    public static void main(String[] args) throws Exception {
        String mode = args[0];
        int port = Integer.parseInt(args[1]);
        backends = List.of(args[2].split(","));
        if (mode.equals("l4")) l4(port, args.length > 3 ? Integer.parseInt(args[3]) : 0);
        else l7(port);
    }

    static String pick() {
        return backends.get(Math.floorMod(NEXT.getAndIncrement(), backends.size()));     // round robin
    }

    static void log(String s) {
        System.out.println(LocalTime.now().format(CLOCK) + "  lb: " + s);
    }

    // ---------------------------------------------------------------- L4: bytes in, bytes out
    static void l4(int port, int idleSeconds) throws IOException {
        AtomicInteger ids = new AtomicInteger();
        try (ServerSocket listener = new ServerSocket(port)) {
            log("L4 on :" + port + " to " + backends + (idleSeconds > 0 ? ", idle timeout " + idleSeconds + " s" : ""));
            while (true) {
                Socket client = listener.accept();
                int id = ids.incrementAndGet();
                Thread.ofVirtual().start(() -> proxy(id, client, idleSeconds));
            }
        }
    }

    static void proxy(int id, Socket client, int idleSeconds) {
        String[] hp = pick().split(":");
        try {
            Socket backend = new Socket(hp[0], Integer.parseInt(hp[1]));          // a second, separate TCP connection
            log("connection " + id + ": client " + client.getInetAddress().getHostAddress() + ":" + client.getPort()
                    + ", backend " + hp[0] + ":" + hp[1] + " from local port " + backend.getLocalPort());
            AtomicLong last = new AtomicLong(System.nanoTime());
            Object state = new Object();
            boolean[] forgotten = {false};
            Thread.ofVirtual().start(() -> pump(backend, client, last, () -> false));
            if (idleSeconds > 0) {
                Thread.ofVirtual().start(() -> {
                    while (!client.isClosed()) {
                        sleep(200);
                        if (System.nanoTime() - last.get() > idleSeconds * 1_000_000_000L) {
                            synchronized (state) { forgotten[0] = true; }
                            log("connection " + id + ": idle for " + idleSeconds + " s, forgotten (backend side closed, client not told)");
                            close(backend);
                            return;
                        }
                    }
                });
            }
            // client to backend: data on a forgotten connection gets a reset, like a cloud NLB
            pump(client, backend, last, () -> {
                synchronized (state) {
                    if (!forgotten[0]) return false;
                }
                log("connection " + id + ": data after the idle timeout, sending a reset");
                try {
                    client.setSoLinger(true, 0);                                     // close() now sends RST, not FIN
                } catch (IOException e) {
                    // already gone
                }
                return true;
            });
            close(client);
            close(backend);
        } catch (IOException e) {
            log("connection " + id + ": " + e);
            close(client);
        }
    }

    interface Check { boolean refuse(); }

    static void pump(Socket from, Socket to, AtomicLong last, Check refuse) {
        byte[] buf = new byte[16 * 1024];
        try {
            InputStream in = from.getInputStream();
            OutputStream out = to.getOutputStream();
            for (int n = in.read(buf); n >= 0; n = in.read(buf)) {
                if (refuse.refuse()) return;
                last.set(System.nanoTime());
                out.write(buf, 0, n);
                out.flush();
            }
            to.shutdownOutput();                                                     // pass the FIN on
        } catch (IOException e) {
            // one side went away
        }
    }

    static void close(Socket s) {
        try {
            s.close();
        } catch (IOException e) {
            // nothing to do
        }
    }

    static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    // ---------------------------------------------------------------- L7: requests in, requests out
    static void l7(int port) throws IOException {
        HttpClient upstream = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build();   // its own pool
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 100);
        server.createContext("/", ex -> {
            String clientIp = ex.getRemoteAddress().getAddress().getHostAddress();
            String xff = ex.getRequestHeaders().getFirst("X-Forwarded-For");
            String target = pick();
            byte[] body = ex.getRequestBody().readAllBytes();
            try {
                HttpRequest req = HttpRequest.newBuilder(URI.create("http://" + target + ex.getRequestURI()))
                        .method(ex.getRequestMethod(), body.length == 0 ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofByteArray(body))
                        .header("X-Forwarded-For", xff == null ? clientIp : xff + ", " + clientIp)   // append, never replace
                        .build();
                HttpResponse<byte[]> r = upstream.send(req, HttpResponse.BodyHandlers.ofByteArray());
                log(ex.getRequestMethod() + " " + ex.getRequestURI() + " from " + clientIp + ":" + ex.getRemoteAddress().getPort() + " to " + target + ": " + r.statusCode());
                ex.sendResponseHeaders(r.statusCode(), r.body().length);
                ex.getResponseBody().write(r.body());
            } catch (Exception e) {
                log(ex.getRequestMethod() + " " + ex.getRequestURI() + " to " + target + " failed: " + e);
                ex.sendResponseHeaders(502, -1);                                         // Bad Gateway
            }
            ex.close();
        });
        server.setExecutor(java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor());
        server.start();
        log("L7 on :" + port + " to " + backends);
    }
}
