package sfz.net.l11.demo;

import java.io.BufferedInputStream;
import java.io.DataInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * A tiny web server that speaks HTTP/1.1 and HTTP/2 on the same port, for lesson 11.
 *
 * Every request takes the same time to answer (300 ms by default), like a card issuer's API. Over
 * HTTP/1.1 a connection carries one request at a time. Over HTTP/2 (cleartext, "prior knowledge":
 * the client starts with the HTTP/2 preface instead of asking to upgrade) every request is a stream,
 * and each stream is answered on its own virtual thread, so they overlap on one connection.
 *
 * It decodes no request headers: the HTTP/2 side answers every stream the same way, so it needs no
 * HPACK decoder. It does follow HTTP/2 flow control: it never sends more DATA than the client's
 * windows allow.
 *
 *   java H2Server.java [port] [delay-ms] [body-bytes]          defaults: 8080 300 20
 *
 * In the lab box:
 *   java /labs/net/src/demo/java/sfz/net/l11/demo/H2Server.java &
 *   curl -s http://127.0.0.1:8080/auth/1                                   HTTP/1.1
 *   curl -s --http2-prior-knowledge http://127.0.0.1:8080/auth/1            HTTP/2
 * On your Mac: ./gradlew :net:demo -Pmain=sfz.net.l11.demo.H2Server
 */
public class H2Server {
    static final byte[] PREFACE = "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n".getBytes(StandardCharsets.US_ASCII);
    static final int DATA = 0, HEADERS = 1, RST_STREAM = 3, SETTINGS = 4, PING = 6, GOAWAY = 7, WINDOW_UPDATE = 8, CONTINUATION = 9;
    static final int END_STREAM = 0x1, ACK = 0x1, END_HEADERS = 0x4;
    static final AtomicInteger CONNECTIONS = new AtomicInteger();
    static int delayMs, bodyBytes;

    public static void main(String[] args) throws Exception {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 8080;
        delayMs = args.length > 1 ? Integer.parseInt(args[1]) : 300;
        bodyBytes = args.length > 2 ? Integer.parseInt(args[2]) : 20;
        try (ServerSocket listener = new ServerSocket(port)) {
            System.out.printf("listening on :%d, every answer takes %d ms%n", port, delayMs);
            while (true) {
                Socket s = listener.accept();
                int id = CONNECTIONS.incrementAndGet();
                Thread.ofVirtual().start(() -> serve(s, id));
            }
        }
    }

    static void serve(Socket s, int conn) {
        String peer = s.getInetAddress().getHostAddress() + ":" + s.getPort();
        try (s) {
            s.setTcpNoDelay(true);
            BufferedInputStream in = new BufferedInputStream(s.getInputStream());
            in.mark(PREFACE.length);
            byte[] first = in.readNBytes(PREFACE.length);
            if (java.util.Arrays.equals(first, PREFACE)) {
                System.out.printf("connection %d from %s: HTTP/2%n", conn, peer);
                new Http2(conn, new DataInputStream(in), s.getOutputStream()).run();
            } else {
                in.reset();
                System.out.printf("connection %d from %s: HTTP/1.1%n", conn, peer);
                http1(conn, in, s.getOutputStream());
            }
        } catch (IOException e) {
            // the client went away
        }
        System.out.printf("connection %d closed%n", conn);
    }

    static byte[] body(String text) {
        StringBuilder b = new StringBuilder(text);
        while (b.length() < bodyBytes - 1) b.append('.');
        return b.append('\n').toString().getBytes(StandardCharsets.US_ASCII);
    }

    // ---------------------------------------------------------------- HTTP/1.1: text, one request at a time
    static void http1(int conn, InputStream in, OutputStream out) throws IOException {
        while (true) {
            String requestLine = line(in);
            if (requestLine == null || requestLine.isEmpty()) return;      // the client closed the connection
            int contentLength = 0;
            boolean close = false;
            for (String h = line(in); h != null && !h.isEmpty(); h = line(in)) {
                String lower = h.toLowerCase();
                if (lower.startsWith("content-length:")) contentLength = Integer.parseInt(h.substring(15).trim());
                if (lower.startsWith("connection:") && lower.contains("close")) close = true;
            }
            in.readNBytes(contentLength);                                  // a request body, if any
            sleep();                                                       // the work: nothing else moves on this connection
            byte[] body = body("hello from connection " + conn);
            String head = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: " + body.length + "\r\n\r\n";
            byte[] h = head.getBytes(StandardCharsets.US_ASCII);
            byte[] response = java.util.Arrays.copyOf(h, h.length + body.length);
            System.arraycopy(body, 0, response, h.length, body.length);
            out.write(response);                                           // one write: see lesson 8 on Nagle
            out.flush();
            System.out.printf("  connection %d: %s -> 200%n", conn, requestLine);
            if (close) return;
        }
    }

    static String line(InputStream in) throws IOException {
        StringBuilder b = new StringBuilder();
        for (int c = in.read(); c != -1; c = in.read()) {
            if (c == '\n') return b.toString().stripTrailing();
            b.append((char) c);
        }
        return b.isEmpty() ? null : b.toString();
    }

    static void sleep() {
        try {
            Thread.sleep(delayMs);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    // ---------------------------------------------------------------- HTTP/2: binary frames, many streams
    static final class Http2 {
        final int conn;
        final DataInputStream in;
        final OutputStream out;
        final Object lock = new Object();             // one writer at a time; also guards the windows
        long connectionWindow = 65_535;               // RFC 9113: every window starts at 65,535 bytes
        int initialStreamWindow = 65_535;             // until the client's SETTINGS say otherwise
        final Map<Integer, long[]> streamWindows = new HashMap<>();

        Http2(int conn, DataInputStream in, OutputStream out) {
            this.conn = conn;
            this.in = in;
            this.out = out;
        }

        void run() throws IOException {
            // our SETTINGS first: SETTINGS_MAX_CONCURRENT_STREAMS (id 3) = 100
            frame(SETTINGS, 0, 0, new byte[]{0, 3, 0, 0, 0, 100});
            while (true) {
                byte[] h = new byte[9];
                try {
                    in.readFully(h);
                } catch (EOFException e) {
                    return;
                }
                int length = ((h[0] & 0xff) << 16) | ((h[1] & 0xff) << 8) | (h[2] & 0xff);
                int type = h[3] & 0xff, flags = h[4] & 0xff;
                int stream = ((h[5] & 0x7f) << 24) | ((h[6] & 0xff) << 16) | ((h[7] & 0xff) << 8) | (h[8] & 0xff);
                byte[] payload = in.readNBytes(length);
                switch (type) {
                    case SETTINGS -> {
                        if ((flags & ACK) == 0) {
                            settings(payload);
                            frame(SETTINGS, ACK, 0, new byte[0]);                   // "got your settings"
                        }
                    }
                    case PING -> {
                        if ((flags & ACK) == 0) frame(PING, ACK, 0, payload);
                    }
                    case WINDOW_UPDATE -> windowUpdate(stream, payload);
                    case HEADERS, DATA, CONTINUATION -> {
                        // a request ends with END_STREAM, on its HEADERS or on its last DATA frame
                        if ((flags & END_STREAM) != 0) {
                            System.out.printf("  connection %d: stream %d request complete%n", conn, stream);
                            Thread.ofVirtual().start(() -> answer(stream));
                        }
                    }
                    case GOAWAY -> {
                        return;
                    }
                    default -> { }                                                   // RST_STREAM, PRIORITY: nothing to do here
                }
            }
        }

        void settings(byte[] p) {
            synchronized (lock) {
                for (int i = 0; i + 6 <= p.length; i += 6) {
                    int id = ((p[i] & 0xff) << 8) | (p[i + 1] & 0xff);
                    long value = ((p[i + 2] & 0xffL) << 24) | ((p[i + 3] & 0xff) << 16) | ((p[i + 4] & 0xff) << 8) | (p[i + 5] & 0xff);
                    if (id == 4) {                                                   // SETTINGS_INITIAL_WINDOW_SIZE
                        long delta = value - initialStreamWindow;
                        initialStreamWindow = (int) value;
                        for (long[] w : streamWindows.values()) w[0] += delta;
                    }
                }
                lock.notifyAll();
            }
        }

        void windowUpdate(int stream, byte[] p) {
            long increment = ((p[0] & 0x7fL) << 24) | ((p[1] & 0xff) << 16) | ((p[2] & 0xff) << 8) | (p[3] & 0xff);
            synchronized (lock) {
                if (stream == 0) connectionWindow += increment;
                else streamWindows.computeIfAbsent(stream, k -> new long[]{initialStreamWindow})[0] += increment;
                lock.notifyAll();
            }
        }

        void answer(int stream) {
            sleep();                                                                 // the work, on this stream only
            byte[] body = body("hello from stream " + stream);
            try {
                // HPACK: 0x88 is static table entry 8, ":status: 200". Then two literals that reuse
                // static names without adding to the table: content-type (31) and content-length (28).
                byte[] type = "text/plain".getBytes(StandardCharsets.US_ASCII);
                byte[] len = Integer.toString(body.length).getBytes(StandardCharsets.US_ASCII);
                byte[] block = new byte[1 + 3 + type.length + 3 + len.length];
                int i = 0;
                block[i++] = (byte) 0x88;
                block[i++] = 0x0f; block[i++] = 0x10; block[i++] = (byte) type.length;
                System.arraycopy(type, 0, block, i, type.length); i += type.length;
                block[i++] = 0x0f; block[i++] = 0x0d; block[i++] = (byte) len.length;
                System.arraycopy(len, 0, block, i, len.length);
                frame(HEADERS, END_HEADERS, stream, block);
                // DATA in frames of at most 16,384 bytes (SETTINGS_MAX_FRAME_SIZE's default)
                int sent = 0;
                while (sent < body.length) {
                    int n = reserve(stream, Math.min(16_384, body.length - sent));
                    byte[] chunk = java.util.Arrays.copyOfRange(body, sent, sent + n);
                    sent += n;
                    frame(DATA, sent == body.length ? END_STREAM : 0, stream, chunk);
                }
                System.out.printf("  connection %d: stream %d -> 200, %d bytes%n", conn, stream, body.length);
            } catch (IOException | InterruptedException e) {
                // the connection is gone
            }
        }

        /** Waits until both the connection's and the stream's windows allow at least one byte, then takes up to [want]. */
        int reserve(int stream, int want) throws InterruptedException {
            synchronized (lock) {
                long[] w = streamWindows.computeIfAbsent(stream, k -> new long[]{initialStreamWindow});
                while (connectionWindow <= 0 || w[0] <= 0) lock.wait();
                int n = (int) Math.min(want, Math.min(connectionWindow, w[0]));
                connectionWindow -= n;
                w[0] -= n;
                return n;
            }
        }

        /** Writes one frame: a 9-byte header (length, type, flags, stream id), then the payload. */
        void frame(int type, int flags, int stream, byte[] payload) throws IOException {
            byte[] f = new byte[9 + payload.length];
            f[0] = (byte) (payload.length >>> 16);
            f[1] = (byte) (payload.length >>> 8);
            f[2] = (byte) payload.length;
            f[3] = (byte) type;
            f[4] = (byte) flags;
            f[5] = (byte) (stream >>> 24);                       // the top bit is reserved and stays 0
            f[6] = (byte) (stream >>> 16);
            f[7] = (byte) (stream >>> 8);
            f[8] = (byte) stream;
            System.arraycopy(payload, 0, f, 9, payload.length);
            synchronized (lock) {
                out.write(f);                                    // header and payload in one write (lesson 8: Nagle)
                out.flush();
            }
        }
    }
}
