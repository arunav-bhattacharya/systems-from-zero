package sfz.cache.l02.demo;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

/** Speaks RESP to Redis over a plain socket, with no client library, and prints every byte. */
public class RespDemo {
    public static void main(String[] args) throws IOException {
        try (Socket socket = new Socket("localhost", 6379)) {
            OutputStream out = socket.getOutputStream();
            InputStream in = socket.getInputStream();
            send(out, in, "PING");
            send(out, in, "SET", "payment:42", "approved");
            send(out, in, "GET", "payment:42");
            send(out, in, "GET", "payment:404");
            send(out, in, "INCR", "auths:today");
            send(out, in, "INCR", "payment:42");
            send(out, in, "HSET", "payment:45", "status", "approved", "amount", "1250");
            send(out, in, "HGETALL", "payment:45");
            send(out, in, "HELLO", "3");                    // switch this connection to RESP3
            send(out, in, "HGETALL", "payment:45");
            send(out, in, "GET", "payment:404");
        }
    }

    // a command is an array of bulk strings: *<count>, then $<length> and the bytes of each word
    static void send(OutputStream out, InputStream in, String... words) throws IOException {
        StringBuilder cmd = new StringBuilder("*" + words.length + "\r\n");
        for (String w : words) {
            cmd.append('$').append(w.getBytes(StandardCharsets.UTF_8).length).append("\r\n").append(w).append("\r\n");
        }
        out.write(cmd.toString().getBytes(StandardCharsets.UTF_8));
        out.flush();
        // good enough for a demo: on loopback a short reply arrives in one read
        byte[] buf = new byte[8192];
        int n = in.read(buf);
        System.out.println("> " + show(cmd.toString(), 200));
        System.out.println("< " + show(new String(buf, 0, n, StandardCharsets.UTF_8), 90));
    }

    static String show(String s, int max) {
        String visible = s.replace("\r\n", "\\r\\n");
        return visible.length() <= max ? visible : visible.substring(0, max) + "... (" + s.length() + " bytes)";
    }
}
