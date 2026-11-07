package sfz.os.l11.demo;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Opens N connections to an echo server and keeps them open, like a pool of mostly idle keep-alive
 * clients. Every 100 ms it sends one line on 20 random connections and reads the echo back.
 * Arguments: N (default 2000), PORT (default 9000), SECONDS to keep going (default 30).
 */
public class IdleClients {
    public static void main(String[] args) throws Exception {
        int n = args.length > 0 ? Integer.parseInt(args[0]) : 2000;
        int port = args.length > 1 ? Integer.parseInt(args[1]) : 9000;
        int seconds = args.length > 2 ? Integer.parseInt(args[2]) : 30;
        List<Socket> conns = new ArrayList<>();
        for (int i = 0; i < n; i++) conns.add(new Socket("127.0.0.1", port));
        System.out.printf("%d connections open%n", n);
        Random rnd = new Random(42);
        byte[] ping = "auth ping\n".getBytes(StandardCharsets.US_ASCII);
        byte[] back = new byte[ping.length];
        long echoes = 0, end = System.nanoTime() + seconds * 1_000_000_000L;
        while (System.nanoTime() < end) {
            for (int k = 0; k < 20; k++) {
                Socket s = conns.get(rnd.nextInt(n));
                OutputStream out = s.getOutputStream();
                out.write(ping);
                InputStream in = s.getInputStream();
                for (int got = 0; got < back.length; ) got += in.read(back, got, back.length - got);
                echoes++;
            }
            Thread.sleep(100);
        }
        System.out.printf("%d echoes received%n", echoes);
        for (Socket s : conns) s.close();
    }
}
